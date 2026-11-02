import json
from pathlib import Path

import pytest
from fixtures.fake_tokenizer import FakeTokenizer, morpheme

from s7.domain.text import Morpheme
from s7builder.quality_report import (
    ModeQuality,
    QualityReport,
    QualityReporter,
    TextQuality,
    find_drops,
    list_standard_texts,
    read_standard_text,
    write_quality_report,
)

# 名詞は 猫(両モードで置き換わる)、未知(辞書に無い)、未登録語(読みが無い。概念版だけ置き換わる)
SENTENCE: list[Morpheme] = [
    morpheme("猫"),
    morpheme("と", "particle"),
    morpheme("未知"),
    morpheme("と", "particle"),
    morpheme("未登録語"),
    morpheme("。", "symbol"),
]
TEXT = "".join(m.surface for m in SENTENCE)
NO_NOUN = "ああ。"


def _texts_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "standard-texts"
    directory.mkdir()
    (directory / "b-cat.txt").write_text(f"# 出典\n# 範囲\n\n{TEXT}\n", encoding="utf-8")
    (directory / "a-empty.txt").write_text(f"{NO_NOUN}\n", encoding="utf-8")
    (directory / "readme.md").write_text("対象外", encoding="utf-8")
    return directory


def test_read_standard_text_skips_source_lines_and_one_blank_line(tmp_path: Path) -> None:
    # Given: 本文の途中の '#' と空行は残す
    path = tmp_path / "text.txt"
    path.write_text("# 出典\n# 範囲\n\n本文1\n\n# 本文の中の行\n", encoding="utf-8")

    # When / Then
    assert read_standard_text(path) == "本文1\n\n# 本文の中の行"


def test_list_standard_texts_returns_txt_files_by_name(tmp_path: Path) -> None:
    texts = list_standard_texts(_texts_dir(tmp_path))

    assert texts == [("a-empty", NO_NOUN), ("b-cat", TEXT)]


def test_report_counts_replaced_nouns_in_both_modes(small_dictionary: Path, tmp_path: Path) -> None:
    # Given
    reporter = QualityReporter(FakeTokenizer(sentences={TEXT: SENTENCE, NO_NOUN: []}))

    # When
    report = reporter.report(small_dictionary, _texts_dir(tmp_path))

    # Then
    assert report.n == 7
    assert report.texts == (
        TextQuality(
            name="a-empty",
            chars=len(NO_NOUN),
            gojuon=ModeQuality(0, 0, 0.0),
            concept=ModeQuality(0, 0, 0.0),
        ),
        TextQuality(
            name="b-cat",
            chars=len(TEXT),
            gojuon=ModeQuality(noun_count=3, replaced_count=1, replaced_rate=33.33),
            concept=ModeQuality(noun_count=3, replaced_count=2, replaced_rate=66.67),
        ),
    )


def _report(gojuon: float, concept: float) -> QualityReport:
    return QualityReport(
        dictionary_version="2026.10.0",
        n=7,
        texts=(
            TextQuality("wagahai", 10, ModeQuality(10, 5, gojuon), ModeQuality(10, 5, concept)),
        ),
    )


def test_write_quality_report_is_stable_json(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "reports" / "quality-report.json"

    # When: 2回書いても同じ
    write_quality_report(_report(50.0, 60.0), path)
    first = path.read_bytes()
    write_quality_report(_report(50.0, 60.0), path)

    # Then
    assert path.read_bytes() == first
    data = json.loads(first)
    assert list(data) == ["dictionary_version", "n", "texts"]
    assert data["texts"][0]["gojuon"] == {
        "noun_count": 10,
        "replaced_count": 5,
        "replaced_rate": 50.0,
    }
    assert first.endswith(b"}\n")


@pytest.mark.parametrize(
    ("gojuon", "concept", "expected"),
    [
        (55.0, 65.01, []),  # 4.99ポイントの低下は知らせない
        (
            55.0,
            65.0,
            ["wagahai・concept: 置換率 65.00% が基準値 70.00% から 5.00 ポイント下がりました"],
        ),
        (
            49.0,
            60.0,
            [
                "wagahai・gojuon: 置換率 49.00% が基準値 55.00% から 6.00 ポイント下がりました",
                "wagahai・concept: 置換率 60.00% が基準値 70.00% から 10.00 ポイント下がりました",
            ],
        ),
        (80.0, 90.0, []),  # 上がったのは知らせない
    ],
)
def test_find_drops_reports_drops_of_five_points_or_more(
    gojuon: float, concept: float, expected: list[str]
) -> None:
    baseline = {"texts": {"wagahai": {"gojuon": 55.0, "concept": 70.0}}}

    assert find_drops(_report(gojuon, concept), baseline) == expected


@pytest.mark.parametrize(
    "baseline",
    [
        {},
        {"texts": []},
        {"texts": {"other": {"gojuon": 99.0}}},
        {"texts": {"wagahai": "壊れた値"}},
        {"texts": {"wagahai": {"gojuon": "99"}}},
    ],
)
def test_find_drops_ignores_missing_or_malformed_baseline(baseline: dict[str, object]) -> None:
    assert find_drops(_report(0.0, 0.0), baseline) == []
