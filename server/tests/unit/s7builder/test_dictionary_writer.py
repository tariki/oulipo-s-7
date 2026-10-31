import sqlite3
import stat
from pathlib import Path

import pytest

from s7.domain.dictionary import DictionaryMeta, Lemma, Sense, Synset
from s7builder.dictionary_writer import DictionaryContents, write_dictionary

META = DictionaryMeta("2026.10.0", "wnjpn-1.1", "core-test", "2026-10-31", 1, 1, 1)


def _contents(senses: list[Sense]) -> DictionaryContents:
    return DictionaryContents(
        lemmas=[Lemma(0, "猫", "ねこ", "ねこ")],
        synsets=[Synset("90000001-n", None, None, None, None, 0, None, None)],
        sibling_groups=[],
        senses=senses,
        meta=META,
        wordnet_license="license",
    )


def test_write_dictionary_is_readable_by_others(tmp_path: Path) -> None:
    """コンテナの実行ユーザー(所有者以外)も読めるようにする。"""
    output = tmp_path / "s7dict.sqlite"

    write_dictionary(_contents([Sense(0, "90000001-n", 0, 0)]), output)

    assert stat.S_IMODE(output.stat().st_mode) == 0o644


def test_write_dictionary_with_dangling_reference_fails(tmp_path: Path) -> None:
    # Given: 語義が無い概念を指している
    output = tmp_path / "s7dict.sqlite"

    # When / Then
    with pytest.raises(sqlite3.IntegrityError, match="sense の行 1 → synset"):
        write_dictionary(_contents([Sense(0, "99999999-n", 0, 0)]), output)
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []
