import sqlite3
from collections.abc import Iterator
from dataclasses import fields

import pytest

from s7.domain.dictionary import Lemma, Sense, Synset
from s7.repositories.dictionary_schema import SCHEMA_SQL, TABLES


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_SQL)
    yield connection
    connection.close()


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def test_schema_creates_all_tables(connection: sqlite3.Connection) -> None:
    names = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

    assert names == set(TABLES)


@pytest.mark.parametrize(
    ("table", "entity"), [("lemma", Lemma), ("synset", Synset), ("sense", Sense)]
)
def test_schema_columns_match_entity_fields(
    connection: sqlite3.Connection, table: str, entity: type
) -> None:
    """テーブルの列とエンティティの項目が、名前と順番まで一致する(辞書の読み書きで対応させるため)。"""
    assert _columns(connection, table) == [f.name for f in fields(entity)]


def test_schema_rejects_unknown_parent_relation(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO synset (id, parent_relation) VALUES ('90000001-n', 'part')")
