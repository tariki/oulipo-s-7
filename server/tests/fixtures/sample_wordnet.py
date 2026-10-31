"""テスト用の小さな日本語WordNet(wnjpn_sample.sql)と、それに合わせた読み・除外リスト。"""

import sqlite3
from pathlib import Path
from typing import Final

SAMPLE_SQL: Final = Path(__file__).with_name("wnjpn_sample.sql")

# FakeTokenizer に渡す読み。かなだけの表記(ネコ、キツネ、ル・コルビュジエ)は Tokenizer を使わない。
# 「未登録語」は載せない(未知語として読みが決まらない)
SAMPLE_READINGS: Final = {
    "実体": "ジッタイ",
    "動物": "ドウブツ",
    "物": "モノ",
    "猫": "ネコ",
    "犬": "イヌ",
    "三毛猫": "ミケネコ",
    "東京": "トウキョウ",
}

# 「存在しない語」は見出し語に無い(リストの語数には数えるが、除外した数には数えない)
SAMPLE_EXCLUDED: Final = "# テスト用\n禁止語\n存在しない語\n"


def create_sample_wordnet(path: Path) -> Path:
    """wnjpn_sample.sql から wnjpn.db の代わりになるSQLiteのファイルを作る。"""
    with sqlite3.connect(path) as connection:
        connection.executescript(SAMPLE_SQL.read_text(encoding="utf-8"))
    connection.close()
    return path
