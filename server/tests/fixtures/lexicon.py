"""見出し語の表記だけを持つ変換用辞書を作る。名詞抽出(引き当て)のテスト用。

置き換えまで確かめるテストは、wnjpn_sample.sql から作る small_repo(conftest.py)を使う。
"""

from collections.abc import Iterable

from s7.domain.dictionary import DictionaryMeta, Lemma, Sense, Synset
from s7.repositories.dictionary_repository import DictionaryData, DictionaryRepository


def make_lexicon(surfaces: Iterable[str]) -> DictionaryRepository:
    """表記ごとに見出し語と概念を1つずつ持つ辞書を作る(どの語も読みは「あ」)。"""
    ordered = sorted(set(surfaces))
    lemmas = tuple(Lemma(i, surface, "あ", "あ\x000\x000") for i, surface in enumerate(ordered))
    synsets = tuple(
        Synset(f"{90000000 + i}-n", None, None, None, None, i, None, None)
        for i in range(len(ordered))
    )
    senses = tuple(Sense(i, f"{90000000 + i}-n", 0, 0) for i in range(len(ordered)))
    meta = DictionaryMeta(
        "test", "wnjpn-1.1", "core-test", "2026-10-31", len(ordered), len(ordered), len(ordered)
    )
    return DictionaryRepository(DictionaryData(lemmas, synsets, (), senses, meta))
