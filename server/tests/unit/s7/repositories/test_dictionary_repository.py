import dataclasses
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from fixtures.lexicon import make_lexicon

from s7.domain.dictionary import Sense, SiblingGroup, Synset
from s7.domain.errors import DictionaryIntegrityError
from s7.repositories.dictionary_repository import DictionaryData, DictionaryRepository


def test_find_lemma_and_lemma_by_id(small_repo: DictionaryRepository) -> None:
    lemma = small_repo.find_lemma("猫")

    assert lemma is not None
    assert (lemma.id, lemma.surface, lemma.reading) == (6, "猫", "ねこ")
    assert small_repo.lemma(6) == lemma
    assert small_repo.find_lemma("存在しない") is None
    assert small_repo.find_lemma("禁止語") is None  # 除外リストの語は見出し語に無い


def test_gojuon_lemma_count_excludes_lemmas_without_reading(
    small_repo: DictionaryRepository,
) -> None:
    assert small_repo.gojuon_lemma_count() == 10
    assert small_repo.lemma(10).reading is None


def test_senses_of_returns_rank_order(small_repo: DictionaryRepository) -> None:
    assert [s.synset_id for s in small_repo.senses_of(0)] == ["90000041-n", "90000012-n"]  # 犬


def test_synset_and_lemmas_of_synset(small_repo: DictionaryRepository) -> None:
    synset = small_repo.synset("90000011-n")

    assert synset is not None
    assert synset.representative_lemma_id == 5
    assert [lemma.surface for lemma in small_repo.lemmas_of_synset("90000011-n")] == ["ネコ", "猫"]
    assert small_repo.lemmas_of_synset("90000010-n") == []  # 見出し語の無い概念
    assert small_repo.synset("99999999-n") is None


def test_sibling_group_keeps_member_order(small_repo: DictionaryRepository) -> None:
    group = small_repo.sibling_group(2)

    assert group == SiblingGroup(
        2, "90000010-n", ("90000012-n", "90000013-n", "90000011-n", "90000015-n")
    )


def test_meta(small_repo: DictionaryRepository) -> None:
    meta = small_repo.meta()

    assert (meta.lemma_count, meta.gojuon_lemma_count, meta.synset_count) == (11, 10, 15)
    assert meta.sudachidict_version == "core-test"


def test_load_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        DictionaryRepository.load(tmp_path / "missing.sqlite")
    assert not (tmp_path / "missing.sqlite").exists()


def test_load_without_meta_key_fails(tmp_path: Path) -> None:
    # Given: meta から built_at を消した辞書
    path = tmp_path / "s7dict.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            "CREATE TABLE lemma (id, surface, reading, sort_key);"
            "CREATE TABLE synset (id, parent_id, parent_relation, sibling_group_id, sibling_index,"
            " representative_lemma_id, definition_ja, definition_en);"
            "CREATE TABLE sibling_group (id, parent_id);"
            "CREATE TABLE sense (lemma_id, synset_id, score, rank);"
            "CREATE TABLE meta (key, value);"
            "INSERT INTO meta VALUES ('dictionary_version', 'x');"
        )
    connection.close()

    # When / Then
    with pytest.raises(DictionaryIntegrityError, match="メタ情報 wordnet_version"):
        DictionaryRepository.load(path)


def _data() -> DictionaryData:
    lexicon = make_lexicon(["語A", "語B"])
    return DictionaryData(
        lemmas=(lexicon.lemma(0), lexicon.lemma(1)),
        synsets=(
            Synset("90000000-n", None, None, None, None, 0, None, None),
            Synset("90000001-n", None, None, None, None, 1, None, None),
        ),
        sibling_groups=(),
        senses=(Sense(0, "90000000-n", 0, 0), Sense(1, "90000001-n", 0, 0)),
        meta=lexicon.meta(),
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda d: dataclasses.replace(
                d, synsets=(dataclasses.replace(d.synsets[0], parent_id="99999999-n"), d.synsets[1])
            ),
            "概念 99999999-n",
        ),
        (
            lambda d: dataclasses.replace(
                d, sibling_groups=(SiblingGroup(0, "90000000-n", ("99999999-n",)),)
            ),
            "概念 99999999-n",
        ),
        (
            lambda d: dataclasses.replace(
                d,
                synsets=(
                    dataclasses.replace(d.synsets[0], representative_lemma_id=5),
                    d.synsets[1],
                ),
            ),
            "見出し語 5",
        ),
        (
            lambda d: dataclasses.replace(d, senses=(Sense(0, "99999999-n", 0, 0),)),
            "概念 99999999-n",
        ),
        (lambda d: dataclasses.replace(d, senses=(d.senses[0],)), "見出し語の語義 1"),
        (lambda d: dataclasses.replace(d, lemmas=(d.lemmas[1], d.lemmas[0])), "見出し語 0"),
        (
            lambda d: dataclasses.replace(
                d, meta=dataclasses.replace(d.meta, gojuon_lemma_count=1)
            ),
            "五十音順リストの見出し語 1",
        ),
        (
            lambda d: dataclasses.replace(d, meta=dataclasses.replace(d.meta, lemma_count=3)),
            "見出し語の数 2",
        ),
        # 兄弟グループの番号が無い
        (
            lambda d: dataclasses.replace(
                d, synsets=(dataclasses.replace(d.synsets[0], sibling_group_id=9), d.synsets[1])
            ),
            "兄弟グループ 9",
        ),
        # メンバーの位置(sibling_index)がグループの並びと合わない
        (
            lambda d: dataclasses.replace(
                d,
                synsets=(
                    dataclasses.replace(d.synsets[0], sibling_group_id=0, sibling_index=1),
                    dataclasses.replace(
                        d.synsets[1], parent_id="90000000-n", parent_relation="hypernym"
                    ),
                ),
                sibling_groups=(SiblingGroup(0, "90000000-n", ("90000000-n",)),),
            ),
            "兄弟グループの並びが不正な概念 90000000-n",
        ),
        # 代表語の無いメンバー
        (
            lambda d: dataclasses.replace(
                d,
                synsets=(
                    dataclasses.replace(
                        d.synsets[0],
                        sibling_group_id=0,
                        sibling_index=0,
                        representative_lemma_id=None,
                    ),
                    d.synsets[1],
                ),
                sibling_groups=(SiblingGroup(0, "90000001-n", ("90000000-n",)),),
            ),
            "兄弟グループの並びが不正な概念 90000000-n",
        ),
        # 上位語が循環している
        (
            lambda d: dataclasses.replace(
                d,
                synsets=(
                    dataclasses.replace(
                        d.synsets[0], parent_id="90000001-n", parent_relation="hypernym"
                    ),
                    dataclasses.replace(
                        d.synsets[1], parent_id="90000000-n", parent_relation="hypernym"
                    ),
                ),
            ),
            "上位語が循環している概念",
        ),
    ],
)
def test_repository_rejects_inconsistent_data(
    change: Callable[[DictionaryData], DictionaryData], message: str
) -> None:
    data = change(_data())

    with pytest.raises(DictionaryIntegrityError, match=message):
        DictionaryRepository(data)


def test_load_with_non_integer_meta_fails(tmp_path: Path) -> None:
    # Given: 本物の形の辞書の lemma_count を数字でない値にする
    path = tmp_path / "s7dict.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            "CREATE TABLE lemma (id, surface, reading, sort_key);"
            "CREATE TABLE synset (id, parent_id, parent_relation, sibling_group_id, sibling_index,"
            " representative_lemma_id, definition_ja, definition_en);"
            "CREATE TABLE sibling_group (id, parent_id);"
            "CREATE TABLE sense (lemma_id, synset_id, score, rank);"
            "CREATE TABLE meta (key, value);"
        )
        connection.executemany(
            "INSERT INTO meta VALUES (?, ?)",
            [
                ("dictionary_version", "x"),
                ("wordnet_version", "x"),
                ("sudachidict_version", "x"),
                ("built_at", "x"),
                ("lemma_count", "多い"),
                ("gojuon_lemma_count", "0"),
                ("synset_count", "0"),
            ],
        )
    connection.close()

    with pytest.raises(DictionaryIntegrityError, match="整数のメタ情報 lemma_count"):
        DictionaryRepository.load(path)


@pytest.mark.parametrize("lemma_id", [-1, 11])
def test_lemma_out_of_range_fails(small_repo: DictionaryRepository, lemma_id: int) -> None:
    with pytest.raises(IndexError):
        small_repo.lemma(lemma_id)
