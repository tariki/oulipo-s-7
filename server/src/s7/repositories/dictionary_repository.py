"""変換用辞書(s7dict.sqlite)を読み込み、メモリ上の索引から引く。

起動時に一度だけ読み込み、実行時はSQLiteを引かない(docs/development-guidelines.md「パフォーマンス」)。
"""

import sqlite3
from collections import defaultdict
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from s7.domain.dictionary import (
    DictionaryMeta,
    Lemma,
    ParentRelation,
    Sense,
    SiblingGroup,
    Synset,
)
from s7.domain.errors import DictionaryIntegrityError


@dataclass(frozen=True, slots=True)
class DictionaryData:
    """変換用辞書の中身。どの並びも主キーの順。"""

    lemmas: tuple[Lemma, ...]
    synsets: tuple[Synset, ...]
    sibling_groups: tuple[SiblingGroup, ...]
    senses: tuple[Sense, ...]
    meta: DictionaryMeta


class DictionaryRepository:
    """変換用辞書の索引。"""

    def __init__(self, data: DictionaryData) -> None:
        """索引を作り、整合性を検査する。

        Args:
            data: 変換用辞書の中身。

        Raises:
            DictionaryIntegrityError: 参照先の無い行があるとき。
        """
        self._lemmas = data.lemmas
        self._meta = data.meta
        self._lemma_by_surface = {lemma.surface: lemma for lemma in data.lemmas}
        self._synsets = {synset.id: synset for synset in data.synsets}
        self._groups = {group.id: group for group in data.sibling_groups}
        senses: defaultdict[int, list[Sense]] = defaultdict(list)
        lemma_ids: defaultdict[str, list[int]] = defaultdict(list)
        for sense in sorted(data.senses, key=lambda s: (s.lemma_id, s.rank)):
            senses[sense.lemma_id].append(sense)
            lemma_ids[sense.synset_id].append(sense.lemma_id)
        self._senses = {lemma_id: tuple(items) for lemma_id, items in senses.items()}
        self._lemma_ids_of_synset = {k: tuple(sorted(v)) for k, v in lemma_ids.items()}
        _check_integrity(data)

    @classmethod
    def load(cls, path: Path) -> "DictionaryRepository":
        """変換用辞書のファイルを読み取り専用で開いて読み込む。

        Args:
            path: s7dict.sqlite のパス。

        Returns:
            読み込んだ辞書。

        Raises:
            FileNotFoundError: ファイルが無いとき(SQLiteが空のファイルを作らないよう、
                開く前に確かめる)。
            DictionaryIntegrityError: 参照先の無い行があるとき。
        """
        if not path.is_file():
            raise FileNotFoundError(path)
        uri = f"{path.resolve().as_uri()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            return cls(_read(connection))

    def find_lemma(self, surface: str) -> Lemma | None:
        """表記から見出し語を引く。"""
        return self._lemma_by_surface.get(surface)

    def lemma(self, lemma_id: int) -> Lemma:
        """番号から見出し語を引く。

        Raises:
            IndexError: 番号が範囲外のとき(負の番号も、末尾から数えずに断る)。
        """
        if not 0 <= lemma_id < len(self._lemmas):
            raise IndexError(lemma_id)
        return self._lemmas[lemma_id]

    def gojuon_lemma_count(self) -> int:
        """五十音順リストの語数(読みのある見出し語の数)。"""
        return self._meta.gojuon_lemma_count

    def senses_of(self, lemma_id: int) -> list[Sense]:
        """見出し語の語義(rank の順)。"""
        return list(self._senses.get(lemma_id, ()))

    def synset(self, synset_id: str) -> Synset | None:
        """概念を引く。"""
        return self._synsets.get(synset_id)

    def lemmas_of_synset(self, synset_id: str) -> list[Lemma]:
        """概念を語義に持つ見出し語(Lemma.id の順)。"""
        return [self._lemmas[i] for i in self._lemma_ids_of_synset.get(synset_id, ())]

    def sibling_group(self, group_id: int) -> SiblingGroup:
        """兄弟グループを引く。"""
        return self._groups[group_id]

    def meta(self) -> DictionaryMeta:
        """辞書のメタ情報。"""
        return self._meta


def _read(connection: sqlite3.Connection) -> DictionaryData:
    lemmas = tuple(
        Lemma(*row)
        for row in connection.execute(
            "SELECT id, surface, reading, sort_key FROM lemma ORDER BY id"
        )
    )
    synsets = tuple(
        Synset(
            id=row[0],
            parent_id=row[1],
            parent_relation=cast("ParentRelation | None", row[2]),
            sibling_group_id=row[3],
            sibling_index=row[4],
            representative_lemma_id=row[5],
            definition_ja=row[6],
            definition_en=row[7],
        )
        for row in connection.execute(
            "SELECT id, parent_id, parent_relation, sibling_group_id, sibling_index,"
            " representative_lemma_id, definition_ja, definition_en FROM synset ORDER BY id"
        )
    )
    members: defaultdict[int, list[tuple[int, str]]] = defaultdict(list)
    for synset in synsets:
        if synset.sibling_group_id is not None and synset.sibling_index is not None:
            members[synset.sibling_group_id].append((synset.sibling_index, synset.id))
    groups = tuple(
        SiblingGroup(
            id=group_id,
            parent_id=parent_id,
            member_ids=tuple(m for _, m in sorted(members[group_id])),
        )
        for group_id, parent_id in connection.execute(
            "SELECT id, parent_id FROM sibling_group ORDER BY id"
        )
    )
    senses = tuple(
        Sense(*row)
        for row in connection.execute(
            "SELECT lemma_id, synset_id, score, rank FROM sense ORDER BY lemma_id, rank"
        )
    )
    meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
    return DictionaryData(lemmas, synsets, groups, senses, _to_meta(meta))


def _to_meta(values: dict[str, str]) -> DictionaryMeta:
    def get(key: str) -> str:
        if key not in values:
            raise DictionaryIntegrityError(key, kind="メタ情報")
        return values[key]

    def get_int(key: str) -> int:
        value = get(key)
        if not (value.isascii() and value.isdigit()):
            raise DictionaryIntegrityError(key, kind="整数のメタ情報")
        return int(value)

    return DictionaryMeta(
        dictionary_version=get("dictionary_version"),
        wordnet_version=get("wordnet_version"),
        sudachidict_version=get("sudachidict_version"),
        built_at=get("built_at"),
        lemma_count=get_int("lemma_count"),
        gojuon_lemma_count=get_int("gojuon_lemma_count"),
        synset_count=get_int("synset_count"),
    )


def _check_integrity(data: DictionaryData) -> None:
    """読み込んだ辞書が、実行時の処理の前提を満たすかを確かめる。"""
    _check_lemmas(data.lemmas, data.meta)
    synset_ids = {synset.id for synset in data.synsets}
    lemma_count = len(data.lemmas)
    for synset in data.synsets:
        if synset.parent_id is not None and synset.parent_id not in synset_ids:
            raise DictionaryIntegrityError(synset.parent_id)
        rep = synset.representative_lemma_id
        if rep is not None and not 0 <= rep < lemma_count:
            raise DictionaryIntegrityError(str(rep), kind="見出し語")
    _check_groups(data)
    _check_no_cycle(data.synsets)
    lemma_ids_with_sense = set()
    for sense in data.senses:
        if sense.synset_id not in synset_ids:
            raise DictionaryIntegrityError(sense.synset_id)
        lemma_ids_with_sense.add(sense.lemma_id)
    missing = set(range(lemma_count)) - lemma_ids_with_sense
    if missing:
        raise DictionaryIntegrityError(str(min(missing)), kind="見出し語の語義")


def _check_groups(data: DictionaryData) -> None:
    """兄弟グループのメンバーが、グループの番号と位置を正しく持ち、代表語を持つこと。

    ConceptShifter は sibling_index でN個先を数え、置換先の代表語を使うため。
    """
    synsets = {synset.id: synset for synset in data.synsets}
    group_ids = {group.id for group in data.sibling_groups}
    for synset in data.synsets:
        if synset.sibling_group_id is not None and synset.sibling_group_id not in group_ids:
            raise DictionaryIntegrityError(str(synset.sibling_group_id), kind="兄弟グループ")
    for group in data.sibling_groups:
        if group.parent_id not in synsets:
            raise DictionaryIntegrityError(group.parent_id)
        for index, member_id in enumerate(group.member_ids):
            member = synsets.get(member_id)
            if member is None:
                raise DictionaryIntegrityError(member_id)
            is_placed = (member.sibling_group_id, member.sibling_index) == (group.id, index)
            if not is_placed or member.representative_lemma_id is None:
                raise DictionaryIntegrityError(member_id, kind="兄弟グループの並びが不正な概念")


def _check_no_cycle(synsets: Sequence[Synset]) -> None:
    """上位語をたどって循環しないこと(ConceptShifter が階層を上がり続けないように)。"""
    parents = {synset.id: synset.parent_id for synset in synsets}
    acyclic: set[str] = set()
    for synset in synsets:
        path: list[str] = []
        current: str | None = synset.id
        while current is not None and current not in acyclic:
            if current in path:
                raise DictionaryIntegrityError(current, kind="上位語が循環している概念")
            path.append(current)
            current = parents.get(current)
        acyclic.update(path)


def _check_lemmas(lemmas: Sequence[Lemma], meta: DictionaryMeta) -> None:
    """見出し語の id が 0 からの連番で、読みのある語が先に並び、数がメタ情報と合うこと。"""
    if len(lemmas) != meta.lemma_count:
        raise DictionaryIntegrityError(str(len(lemmas)), kind="見出し語の数")
    for index, lemma in enumerate(lemmas):
        if lemma.id != index:
            raise DictionaryIntegrityError(str(index), kind="見出し語")
        if (lemma.reading is not None) != (index < meta.gojuon_lemma_count):
            raise DictionaryIntegrityError(str(index), kind="五十音順リストの見出し語")
