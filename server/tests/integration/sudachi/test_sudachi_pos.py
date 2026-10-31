"""本物のSudachiの品詞の値(名詞抽出が前提にしているもの)。SudachiPy・SudachiDictを上げるときに必ず通す。"""

import pytest
from fixtures.lexicon import make_lexicon

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.domain.transform import Noun
from s7.services.noun_extractor import NounExtractor

pytestmark = pytest.mark.sudachi


@pytest.fixture(scope="module")
def tokenizer() -> SudachiTokenizer:
    return SudachiTokenizer()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 機能設計書「最長一致」の例の区切り(モードA)
        (
            "図書館司書",
            [
                ("図書", "名詞", "普通名詞"),
                ("館", "接尾辞", "名詞的"),
                ("司書", "名詞", "普通名詞"),
            ],
        ),
        ("科学者", [("科学", "名詞", "普通名詞"), ("者", "接尾辞", "名詞的")]),
        ("ネコ科", [("ネコ", "名詞", "普通名詞"), ("科", "接尾辞", "名詞的")]),
        ("三角形", [("三", "名詞", "数詞"), ("角形", "接尾辞", "名詞的")]),
        ("子供たち", [("子供", "名詞", "普通名詞"), ("たち", "接尾辞", "名詞的")]),
        # 固有名詞・代名詞・接頭辞・形式名詞
        ("東京湾", [("東京", "名詞", "固有名詞"), ("湾", "名詞", "普通名詞")]),
        ("私", [("私", "代名詞", "*")]),
        ("お茶", [("お", "接頭辞", "*"), ("茶", "名詞", "普通名詞")]),
        ("書くこと", [("書く", "動詞", "一般"), ("こと", "名詞", "普通名詞")]),
    ],
)
def test_mode_a_split_and_pos(
    tokenizer: SudachiTokenizer, text: str, expected: list[tuple[str, str, str]]
) -> None:
    morphemes = tokenizer.tokenize(text, "A")

    assert [(m.surface, *m.pos[:2]) for m in morphemes] == expected


@pytest.mark.parametrize(("text", "normalized"), [("子ども", "子供"), ("ＤＮＡ", "DNA")])
def test_normalized_form(tokenizer: SudachiTokenizer, text: str, normalized: str) -> None:
    [morpheme] = tokenizer.tokenize(text, "A")

    assert morpheme.normalized_form == normalized


def test_extract_with_real_sudachi(tokenizer: SudachiTokenizer) -> None:
    """本物のSudachiと小さな辞書で、機能設計書の例どおりに名詞を取り出す。"""
    # Given
    lexicon = make_lexicon(["図書館", "司書", "科学者", "三角形", "子供", "東京湾", "茶"])
    extractor = NounExtractor(tokenizer, lexicon)
    text = "図書館司書の科学者は、三角形を子供たちと東京湾で見た。私はお茶を書くことにした。"

    # When
    segments = extractor.extract(text)

    # Then
    nouns = [
        (s.surface, s.lemma.surface if s.lemma else None) for s in segments if isinstance(s, Noun)
    ]
    assert nouns == [
        ("図書館", "図書館"),
        ("司書", "司書"),
        ("科学者", "科学者"),
        ("三角形", "三角形"),
        ("子供", "子供"),
        ("東京湾", "東京湾"),
        ("茶", "茶"),
    ]
    assert "".join(s if isinstance(s, str) else s.surface for s in segments) == text
