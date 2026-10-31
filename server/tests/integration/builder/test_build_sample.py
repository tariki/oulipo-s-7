import sqlite3
from pathlib import Path

import pytest
from fixtures.fake_tokenizer import FakeTokenizer
from fixtures.sample_wordnet import SAMPLE_EXCLUDED, SAMPLE_READINGS, create_sample_wordnet

from s7.domain.dictionary import DictionaryMeta
from s7.repositories.dictionary_schema import TABLES
from s7builder.build_report import BuildReport
from s7builder.dictionary_builder import DictionaryBuilder
from s7builder.errors import BuildError

LICENSE = "Japanese WordNet license (test)"


@pytest.fixture
def inputs(tmp_path: Path) -> tuple[Path, Path]:
    excluded = tmp_path / "excluded-lemmas.txt"
    excluded.write_text(SAMPLE_EXCLUDED, encoding="utf-8")
    return create_sample_wordnet(tmp_path / "wnjpn.db"), excluded


def _build(inputs: tuple[Path, Path], output: Path) -> BuildReport:
    builder = DictionaryBuilder(FakeTokenizer(SAMPLE_READINGS), "core-test", LICENSE)
    return builder.build(inputs[0], inputs[1], output)


def _rows(path: Path, sql: str) -> list[tuple[object, ...]]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute(sql).fetchall()
    connection.close()
    return rows


def test_build_orders_lemmas_by_gojuon_then_no_reading(
    inputs: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given
    output = tmp_path / "s7dict.sqlite"

    # When
    _build(inputs, output)

    # Then: 読みのある語の五十音順(同じ読みは表記の文字コード順)、その後ろに読みの無い語
    assert _rows(output, "SELECT id, surface, reading FROM lemma ORDER BY id") == [
        (0, "犬", "いぬ"),
        (1, "キツネ", "きつね"),
        (2, "実体", "じったい"),
        (3, "東京", "とうきょう"),
        (4, "動物", "どうぶつ"),
        (5, "ネコ", "ねこ"),
        (6, "猫", "ねこ"),
        (7, "三毛猫", "みけねこ"),
        (8, "物", "もの"),
        (9, "ル・コルビュジエ", "るこるびゅじえ"),
        (10, "未登録語", None),
    ]
    assert _rows(output, "SELECT sort_key IS NULL FROM lemma WHERE id = 10") == [(1,)]


def test_build_writes_synsets_with_parent_representative_and_group(
    inputs: tuple[Path, Path], tmp_path: Path
) -> None:
    output = tmp_path / "s7dict.sqlite"

    _build(inputs, output)

    synsets = {
        row[0]: row[1:]
        for row in _rows(
            output,
            "SELECT id, parent_id, parent_relation, sibling_group_id, sibling_index,"
            " representative_lemma_id FROM synset",
        )
    }
    assert len(synsets) == 15  # 名詞の概念すべて(動詞の概念は入らない)
    assert synsets["90000001-n"] == (None, None, None, None, 2)  # 最上位
    assert synsets["90000010-n"] == ("90000002-n", "hypernym", None, None, None)  # 見出し語なし
    assert synsets["90000011-n"] == ("90000010-n", "hypernym", 2, 2, 5)  # 代表語はネコ(id 5)
    assert synsets["90000014-n"] == (
        "90000010-n",
        "hypernym",
        None,
        None,
        None,
    )  # 除外で見出し語なし
    assert synsets["90000015-n"] == ("90000010-n", "hypernym", 2, 3, 10)  # 読みの無い語も代表語
    assert synsets["90000020-n"] == ("90000011-n", "hypernym", 3, 0, 7)  # 兄弟が自分だけ
    assert synsets["90000030-n"] == ("90000003-n", "hypernym", 1, 1, 3)  # 上位語は概念IDの小さい方
    assert synsets["90000032-n"] == ("90000031-n", "instance_hypernym", 4, 0, 9)


def test_build_writes_sibling_groups_in_order(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    output = tmp_path / "s7dict.sqlite"

    _build(inputs, output)

    groups = _rows(output, "SELECT id, parent_id FROM sibling_group ORDER BY id")
    members = _rows(
        output,
        "SELECT sibling_group_id, id FROM synset WHERE sibling_group_id IS NOT NULL"
        " ORDER BY sibling_group_id, sibling_index",
    )
    assert groups == [
        (0, "90000001-n"),
        (1, "90000003-n"),
        (2, "90000010-n"),
        (3, "90000011-n"),
        (4, "90000031-n"),
    ]
    assert members == [
        (0, "90000002-n"),
        (0, "90000003-n"),
        (1, "90000041-n"),  # 代表語 犬(0)
        (1, "90000030-n"),  # 東京(3)
        (1, "90000040-n"),  # 猫(6)
        (2, "90000012-n"),  # 犬(0)
        (2, "90000013-n"),  # キツネ(1)
        (2, "90000011-n"),  # ネコ(5)
        (2, "90000015-n"),  # 未登録語(10)
        (3, "90000020-n"),
        (4, "90000032-n"),
    ]


def test_build_ranks_senses_by_english_frequency(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    output = tmp_path / "s7dict.sqlite"

    _build(inputs, output)

    senses = _rows(
        output,
        "SELECT lemma_id, synset_id, score, rank FROM sense"
        " WHERE lemma_id IN (0, 6) ORDER BY lemma_id, rank",
    )
    assert senses == [
        (0, "90000041-n", 9, 0),  # 犬: 頻度の大きい方が先
        (0, "90000012-n", 2, 1),
        (6, "90000011-n", 5, 0),  # 猫: 同点(3 + 2 と 5)は概念IDの順
        (6, "90000040-n", 5, 1),
    ]


def test_build_writes_definitions_joined_by_sid(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    output = tmp_path / "s7dict.sqlite"

    _build(inputs, output)

    assert _rows(
        output, "SELECT definition_ja, definition_en FROM synset WHERE id = '90000011-n'"
    ) == [("ネコ科の動物；家で飼われる", "feline; pet")]
    # 空白だけの定義文は無いものとして扱う
    assert _rows(output, "SELECT definition_en FROM synset WHERE id = '90000012-n'") == [(None,)]


def test_build_returns_report_and_writes_meta(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    output = tmp_path / "s7dict.sqlite"

    report = _build(inputs, output)

    assert report == BuildReport(
        meta=DictionaryMeta(
            dictionary_version=report.meta.dictionary_version,
            wordnet_version="wnjpn-1.1",
            sudachidict_version="core-test",
            built_at=report.meta.built_at,
            lemma_count=11,
            gojuon_lemma_count=10,
            synset_count=15,
        ),
        wordnet_lemma_count=12,
        excluded_list_size=2,
        excluded_lemma_count=1,
        reading_by_kana_count=3,
        reading_by_sudachi_count=7,
        no_reading_count=1,
        sibling_group_count=5,
    )
    meta = {str(key): value for key, value in _rows(output, "SELECT key, value FROM meta")}
    assert meta["license_wordnet"] == LICENSE
    assert meta["gojuon_lemma_count"] == "10"
    assert meta["built_at"] == report.meta.built_at


def test_build_twice_produces_same_rows(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    """決定性: 同じ入力から2回ビルドすると、全テーブルの行と報告が一致する。"""
    # When
    first = _build(inputs, tmp_path / "first.sqlite")
    second = _build(inputs, tmp_path / "second.sqlite")

    # Then
    assert first == second
    for table in TABLES:
        sql = f"SELECT * FROM {table} ORDER BY 1, 2"  # noqa: S608  テーブル名は定数
        assert _rows(tmp_path / "first.sqlite", sql) == _rows(tmp_path / "second.sqlite", sql)


def test_build_without_excluded_list_fails_before_reading_wordnet(tmp_path: Path) -> None:
    # Given: 除外リストも wnjpn.db も無い
    builder = DictionaryBuilder(FakeTokenizer({}), "core-test", LICENSE)

    # When / Then: 先に除外リストの不備で止まる
    with pytest.raises(BuildError, match="除外する語のリストがありません"):
        builder.build(tmp_path / "wnjpn.db", tmp_path / "missing.txt", tmp_path / "out.sqlite")


def test_build_without_wordnet_fails(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    builder = DictionaryBuilder(FakeTokenizer({}), "core-test", LICENSE)

    with pytest.raises(BuildError, match="日本語WordNetのファイルがありません"):
        builder.build(tmp_path / "missing.db", inputs[1], tmp_path / "out.sqlite")

    # 空のデータベースを作らない
    assert not (tmp_path / "missing.db").exists()


def test_build_with_broken_parent_fails_integrity_check(
    inputs: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: 上位語が概念の一覧に無い元データ
    with sqlite3.connect(inputs[0]) as connection:
        connection.execute(
            "INSERT INTO synlink VALUES ('90000001-n', '99999999-n', 'hype', 'test')"
        )
    connection.close()
    output = tmp_path / "s7dict.sqlite"

    # When / Then
    with pytest.raises(BuildError, match="上位語の概念 99999999-n"):
        _build(inputs, output)
    assert not output.exists()


def test_write_keeps_previous_dictionary_when_insert_fails(
    inputs: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """書き込みの途中で失敗したら一時ファイルを消し、前の辞書を残す。"""
    # Given: 前の辞書がある。行の書き込みで失敗させる
    output = tmp_path / "s7dict.sqlite"
    output.write_bytes(b"previous")

    def broken_insert(connection: sqlite3.Connection, contents: object) -> None:
        raise sqlite3.IntegrityError

    monkeypatch.setattr("s7builder.dictionary_writer._insert_rows", broken_insert)

    # When / Then
    with pytest.raises(sqlite3.IntegrityError):
        _build(inputs, output)
    assert output.read_bytes() == b"previous"
    assert list(tmp_path.glob(".s7dict.sqlite.*")) == []
