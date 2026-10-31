"""変換用辞書(s7dict.sqlite)を書き出す。"""

import os
import sqlite3
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from s7.domain.dictionary import DictionaryMeta, Lemma, Sense, SiblingGroup, Synset
from s7.repositories.dictionary_schema import META_LICENSE_WORDNET, SCHEMA_SQL


@dataclass(frozen=True, slots=True)
class DictionaryContents:
    """変換用辞書に書く中身。どの並びも主キーの順。

    Attributes:
        lemmas: 見出し語。
        synsets: 概念。
        sibling_groups: 兄弟グループ。
        senses: 語義。
        meta: メタ情報。
        wordnet_license: 日本語WordNetのライセンス全文。
    """

    lemmas: Sequence[Lemma]
    synsets: Sequence[Synset]
    sibling_groups: Sequence[SiblingGroup]
    senses: Sequence[Sense]
    meta: DictionaryMeta
    wordnet_license: str


def write_dictionary(contents: DictionaryContents, output: Path) -> None:
    """変換用辞書を書く。

    同じディレクトリの一時ファイルに書いてから置き換える(途中で失敗しても前の辞書を壊さない)。

    Args:
        contents: 書く中身。
        output: 出力先のパス。

    Raises:
        sqlite3.IntegrityError: 参照先の無い行があるとき(外部キーの検査)。
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript(SCHEMA_SQL)
            # 外部キーを1行ずつ検査しない。概念は上位語や兄弟グループを互いに
            # 参照し合うため入れる順で失敗するうえ、遅らせて検査しても参照する側の
            # 列に索引が無く、本物の辞書で約6分かかった。書き終えてからまとめて検査する
            # (約6秒)
            with connection:
                _insert_rows(connection, contents)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                table, rowid, parent, _ = violations[0]
                raise sqlite3.IntegrityError(
                    f"外部キーの参照先がありません: {table} の行 {rowid} → {parent}"
                )
        finally:
            connection.close()
        # mkstemp は所有者だけが読める権限で作る。コンテナの実行ユーザーも読めるようにする
        Path(temporary).chmod(0o644)
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _insert_rows(connection: sqlite3.Connection, contents: DictionaryContents) -> None:
    connection.executemany(
        "INSERT INTO lemma (id, surface, reading, sort_key) VALUES (?, ?, ?, ?)",
        [(x.id, x.surface, x.reading, x.sort_key) for x in contents.lemmas],
    )
    connection.executemany(
        "INSERT INTO synset (id, parent_id, parent_relation, sibling_group_id, sibling_index,"
        " representative_lemma_id, definition_ja, definition_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                x.id,
                x.parent_id,
                x.parent_relation,
                x.sibling_group_id,
                x.sibling_index,
                x.representative_lemma_id,
                x.definition_ja,
                x.definition_en,
            )
            for x in contents.synsets
        ],
    )
    connection.executemany(
        "INSERT INTO sibling_group (id, parent_id) VALUES (?, ?)",
        [(g.id, g.parent_id) for g in contents.sibling_groups],
    )
    connection.executemany(
        "INSERT INTO sense (lemma_id, synset_id, score, rank) VALUES (?, ?, ?, ?)",
        [(x.lemma_id, x.synset_id, x.score, x.rank) for x in contents.senses],
    )
    meta = {key: str(value) for key, value in asdict(contents.meta).items()}
    meta[META_LICENSE_WORDNET] = contents.wordnet_license
    connection.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
