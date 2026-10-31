from collections.abc import Sequence

import pytest
from fixtures.fake_tokenizer import FakeTokenizer, MorphemeKind, morpheme
from fixtures.lexicon import make_lexicon

from s7.domain.text import Morpheme
from s7.domain.transform import Noun, RawSegment
from s7.services.noun_extractor import NounExtractor


def _extract(morphemes: Sequence[Morpheme], lexicon: Sequence[str]) -> list[RawSegment]:
    text = "".join(m.surface for m in morphemes)
    extractor = NounExtractor(FakeTokenizer(sentences={text: morphemes}), make_lexicon(lexicon))
    segments = extractor.extract(text)
    # どの場合も、つなげると元の文章に戻る
    assert "".join(s if isinstance(s, str) else s.surface for s in segments) == text
    return segments


def _shape(segments: Sequence[RawSegment]) -> list[str | tuple[str, str | None]]:
    """文字列はそのまま、名詞は(表記, 引き当てた見出し語)にする。"""
    return [
        s if isinstance(s, str) else (s.surface, s.lemma.surface if s.lemma else None)
        for s in segments
    ]


def _m(*items: tuple[str, MorphemeKind]) -> list[Morpheme]:
    return [morpheme(surface, kind) for surface, kind in items]


@pytest.mark.parametrize(
    ("morphemes", "lexicon", "expected"),
    [
        # 機能設計書「最長一致」の例
        (
            _m(("図書", "noun"), ("館", "suffix"), ("司書", "noun")),
            ["図書館", "図書", "司書"],
            [("図書館", "図書館"), ("司書", "司書")],
        ),
        (_m(("科学", "noun"), ("者", "suffix")), ["科学者", "科学"], [("科学者", "科学者")]),
        (_m(("ネコ", "noun"), ("科", "suffix")), ["ネコ科", "ネコ"], [("ネコ科", "ネコ科")]),
        (_m(("三", "numeral"), ("角形", "suffix")), ["三角形"], [("三角形", "三角形")]),
        # 「子供たち」が辞書に無ければ「子供」だけ。「たち」は文字列として残る
        (_m(("子供", "noun"), ("たち", "suffix")), ["子供"], [("子供", "子供"), "たち"]),
        # 固有名詞を含む複合語は、辞書にあれば1語
        (_m(("東京", "proper"), ("湾", "noun")), ["東京湾"], [("東京湾", "東京湾")]),
    ],
)
def test_extract_merges_compounds_in_dictionary(
    morphemes: list[Morpheme], lexicon: list[str], expected: list[object]
) -> None:
    assert _shape(_extract(morphemes, lexicon)) == expected


def test_extract_keeps_single_common_noun_not_in_dictionary() -> None:
    """1形態素の普通名詞は、辞書に無くても名詞にする(not_in_dictionary として表示するため)。"""
    assert _shape(_extract(_m(("未知語", "noun")), [])) == [("未知語", None)]


@pytest.mark.parametrize(
    ("surface", "kind"),
    [
        ("東京", "proper"),  # 単独の固有名詞
        ("三", "numeral"),  # 単独の数詞
        ("館", "suffix"),  # 単独の接尾辞
        ("御", "prefix"),  # 単独の接頭辞
        ("私", "pronoun"),  # 代名詞
    ],
)
def test_extract_skips_non_target_single_morpheme(surface: str, kind: MorphemeKind) -> None:
    # Given: 辞書にあっても対象外
    segments = _extract(_m((surface, kind)), [surface])

    assert segments == [surface]


def test_extract_skips_formal_noun_by_surface() -> None:
    """形式名詞は表記で判定する。「こと」は対象外、「事」は対象。"""
    segments = _extract(
        _m(("書く", "verb"), ("こと", "noun"), ("と", "particle"), ("事", "noun")),
        ["こと", "事"],
    )

    assert _shape(segments) == ["書くことと", ("事", "事")]


def test_extract_pronoun_breaks_candidate_run() -> None:
    """代名詞は候補区間に入らないため、前後の語をつなげない。"""
    segments = _extract(_m(("猫", "noun"), ("私", "pronoun"), ("達", "suffix")), ["猫私達", "猫"])

    assert _shape(segments) == [("猫", "猫"), "私達"]


@pytest.mark.parametrize(
    ("item", "lexicon", "lemma"),
    [
        (morpheme("ＤＮＡ"), ["DNA"], "DNA"),  # NFKC
        (morpheme("子ども", normalized_form="子供"), ["子供"], "子供"),  # 正規化表記
        (morpheme("猫", normalized_form="ネコ"), ["猫", "ネコ"], "猫"),  # 表記が先
    ],
)
def test_lookup_order(item: Morpheme, lexicon: list[str], lemma: str) -> None:
    assert _shape(_extract([item], lexicon)) == [(item.surface, lemma)]


def test_lookup_uses_normalized_form_only_for_single_morpheme() -> None:
    # Given: 「子ども達」の正規化表記をつなげた「子供達」は辞書にあるが、2形態素なので使わない
    morphemes = [morpheme("子ども", normalized_form="子供"), morpheme("達", "suffix")]

    # When
    segments = _extract(morphemes, ["子供達", "子供"])

    # Then: 1形態素の「子ども」だけが正規化表記で見つかる
    assert _shape(segments) == [("子ども", "子供"), "達"]


def test_extract_window_is_eight_morphemes() -> None:
    # Given: 9形態素の連結と8形態素の連結が辞書にある
    morphemes = [morpheme(c) for c in "ABCDEFGHI"]

    # When
    segments = _extract(morphemes, ["ABCDEFGHI", "ABCDEFGH"])

    # Then: 9形態素は試さず、8形態素でまとめる
    assert _shape(segments) == [("ABCDEFGH", "ABCDEFGH"), ("I", None)]


def test_extract_finds_compound_across_window_boundary() -> None:
    """区間を8個ずつに切らないため、10形態素の区間の9・10個目にまたがる辞書語も見つかる。"""
    morphemes = [morpheme(c) for c in "ABCDEFGHIJ"]

    segments = _extract(morphemes, ["HIJ"])

    assert _shape(segments)[-1] == ("HIJ", "HIJ")
    assert len(segments) == 8


def test_extract_joins_non_noun_strings() -> None:
    segments = _extract(
        _m(("猫", "noun"), ("が", "particle"), ("、", "symbol"), (" ", "space"), ("犬", "noun")),
        ["猫", "犬"],
    )

    assert _shape(segments) == [("猫", "猫"), "が、 ", ("犬", "犬")]
    assert all(isinstance(s, Noun) or s for s in segments)


def test_extract_does_not_merge_across_chunk_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: 長文の分割で「図書」と「館」が別の部分になる
    monkeypatch.setattr(
        "s7.services.noun_extractor.split_for_tokenizer", lambda text: ["本の図書", "館"]
    )
    tokenizer = FakeTokenizer(
        sentences={
            "本の図書": _m(("本", "noun"), ("の", "particle"), ("図書", "noun")),
            "館": _m(("館", "suffix")),
        }
    )
    extractor = NounExtractor(tokenizer, make_lexicon(["図書館", "図書", "本"]))

    # When
    segments = extractor.extract("本の図書館")

    # Then
    assert _shape(segments) == [("本", "本"), "の", ("図書", "図書"), "館"]


def test_extract_compound_needs_common_noun_or_suffix() -> None:
    """固有名詞と数詞だけの連結は、辞書にあっても1語にしない。"""
    segments = _extract(_m(("東京", "proper"), ("3", "numeral")), ["東京3"])

    assert segments == ["東京3"]
