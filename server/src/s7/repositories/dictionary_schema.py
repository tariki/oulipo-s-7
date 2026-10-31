"""変換用辞書のテーブル定義。辞書ビルダーとサーバーで共有する。

機能設計書「変換用辞書のテーブル定義」と同じ内容。変えたら両方を直す。
"""

from typing import Final

SCHEMA_SQL: Final = """
CREATE TABLE lemma (
  id        INTEGER PRIMARY KEY,
  surface   TEXT NOT NULL UNIQUE,
  reading   TEXT,
  sort_key  TEXT
);
CREATE TABLE synset (
  id                      TEXT PRIMARY KEY,
  parent_id               TEXT REFERENCES synset(id),
  parent_relation         TEXT CHECK (parent_relation IN ('hypernym', 'instance_hypernym')),
  sibling_group_id        INTEGER REFERENCES sibling_group(id),
  sibling_index           INTEGER,
  representative_lemma_id INTEGER REFERENCES lemma(id),
  definition_ja           TEXT,
  definition_en           TEXT
);
CREATE TABLE sibling_group (
  id        INTEGER PRIMARY KEY,
  parent_id TEXT NOT NULL REFERENCES synset(id)
);
CREATE TABLE sense (
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  synset_id TEXT NOT NULL REFERENCES synset(id),
  score     INTEGER NOT NULL,
  rank      INTEGER NOT NULL,
  PRIMARY KEY (lemma_id, synset_id)
);
-- キーと値の組で持つ。DictionaryMetaの各項目と、license_wordnet(日本語WordNetのライセンス全文)
CREATE TABLE meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

# 書き込み・比較のときに使うテーブルの一覧(外部キーの参照先が先)
TABLES: Final = ("lemma", "synset", "sibling_group", "sense", "meta")

# meta テーブルのうち、DictionaryMeta 以外の項目のキー
META_LICENSE_WORDNET: Final = "license_wordnet"
