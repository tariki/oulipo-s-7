"""日本語WordNet(wnjpn.db)から、変換用辞書に必要なデータを読む(WordNetReader)。"""

import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from s7.domain.dictionary import ParentRelation
from s7builder.errors import BuildError

_RELATIONS: Final[Mapping[str, ParentRelation]] = {
    "hype": "hypernym",
    "inst": "instance_hypernym",
}
# 定義文が複数の文(sid)に分かれているときのつなぎ方(sid の順)
_DEFINITION_SEPARATORS: Final[Mapping[str, str]] = {"jpn": "；", "eng": "; "}

_LEMMAS_SQL: Final = """
SELECT w.lemma, s.synset FROM word AS w JOIN sense AS s ON s.wordid = w.wordid
WHERE w.lang = 'jpn' AND w.pos = 'n' AND s.lang = 'jpn' AND s.synset LIKE '%-n'
"""
_SYNSETS_SQL: Final = "SELECT synset FROM synset WHERE pos = 'n'"
_LINKS_SQL: Final = """
SELECT synset1, synset2, link FROM synlink
WHERE link IN ('hype', 'inst') AND synset1 LIKE '%-n'
"""
_DEFINITIONS_SQL: Final = """
SELECT synset, lang, CAST(sid AS INTEGER), def FROM synset_def
WHERE lang IN ('jpn', 'eng') AND synset LIKE '%-n'
"""
_FREQUENCIES_SQL: Final = """
SELECT synset, SUM(COALESCE(freq, 0)) FROM sense
WHERE lang = 'eng' AND synset LIKE '%-n' GROUP BY synset
"""


@dataclass(frozen=True, slots=True)
class WordNetData:
    """日本語WordNetから読んだデータ。どの並びも概念ID・表記の文字コード順。

    Attributes:
        lemma_synsets: 日本語の名詞の見出し語の表記 → その語義の概念ID。
        synset_ids: 名詞の概念ID(日本語の見出し語を持たない概念を含む)。
        parent_candidates: 概念ID → 上位語の候補(概念ID, 関係)。
        definitions_ja: 概念ID → 日本語の定義文。
        definitions_en: 概念ID → 英語の定義文。
        english_frequencies: 概念ID → 英語の語義の頻度の合計。
    """

    lemma_synsets: Mapping[str, tuple[str, ...]]
    synset_ids: tuple[str, ...]
    parent_candidates: Mapping[str, tuple[tuple[str, ParentRelation], ...]]
    definitions_ja: Mapping[str, str]
    definitions_en: Mapping[str, str]
    english_frequencies: Mapping[str, int]


def read_wordnet(path: Path) -> WordNetData:
    """wnjpn.db を読み取り専用で開いて読む。

    Args:
        path: wnjpn.db のパス。

    Returns:
        読んだデータ。

    Raises:
        BuildError: ファイルが無い(SQLiteが空のデータベースを作らないよう、開く前に確かめる)、
            または日本語WordNetとして読めないとき。
    """
    if not path.is_file():
        raise BuildError(f"日本語WordNetのファイルがありません: {path}")
    try:
        return _read(path)
    except sqlite3.DatabaseError as error:
        raise BuildError(f"日本語WordNetとして読めません: {path}") from error


def _read(path: Path) -> WordNetData:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        lemma_synsets = _group_sorted(connection.execute(_LEMMAS_SQL))
        synset_ids = tuple(sorted(row[0] for row in connection.execute(_SYNSETS_SQL)))
        parent_candidates = _group_sorted(
            (synset, (parent, _RELATIONS[link]))
            for synset, parent, link in connection.execute(_LINKS_SQL)
        )
        definitions = _read_definitions(connection)
        frequencies = {synset: int(total) for synset, total in connection.execute(_FREQUENCIES_SQL)}
    return WordNetData(
        lemma_synsets=lemma_synsets,
        synset_ids=synset_ids,
        parent_candidates=parent_candidates,
        definitions_ja=definitions["jpn"],
        definitions_en=definitions["eng"],
        english_frequencies=dict(sorted(frequencies.items())),
    )


def _group_sorted[V: (str, tuple[str, ParentRelation])](
    pairs: Iterable[tuple[str, V]],
) -> dict[str, tuple[V, ...]]:
    grouped: defaultdict[str, set[V]] = defaultdict(set)
    for key, value in pairs:
        grouped[key].add(value)
    return {key: tuple(sorted(grouped[key])) for key in sorted(grouped)}


def _read_definitions(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    """言語ごとに、概念ID → 定義文を返す。

    wnjpn.db には、同じ (概念, 言語, sid) の行が複数あることがある(英語は全概念で2行。
    同じ文の繰り返しか、例文付きと例文なしの版)。sid ごとに最も短い文(同じ長さなら文字コード順で
    先の文)を1つ選び、sid の順につなぐ。別の sid と同じ文は省く。
    """
    chosen: dict[tuple[str, str, int], str] = {}
    for synset, lang, sid, raw in connection.execute(_DEFINITIONS_SQL):
        text = (raw or "").strip()
        key = (synset, lang, sid)
        if text and (key not in chosen or (len(text), text) < (len(chosen[key]), chosen[key])):
            chosen[key] = text
    parts: dict[str, defaultdict[str, list[str]]] = {
        lang: defaultdict(list) for lang in _DEFINITION_SEPARATORS
    }
    for synset, lang, sid in sorted(chosen):
        # 別の sid に同じ文が入っていることがある(日本語で25件)。同じ文は1回だけつなぐ
        if chosen[synset, lang, sid] not in parts[lang][synset]:
            parts[lang][synset].append(chosen[synset, lang, sid])
    return {
        lang: _join(parts[lang], separator) for lang, separator in _DEFINITION_SEPARATORS.items()
    }


def _join(parts: Mapping[str, list[str]], separator: str) -> dict[str, str]:
    return {synset: separator.join(parts[synset]) for synset in sorted(parts)}
