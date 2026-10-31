-- テスト用の小さな日本語WordNet。概念IDは架空(9で始まる)。
-- 本物の wnjpn.db と同じテーブル定義のうち、辞書ビルダーが読むものだけを持つ。
--
-- 概念の木(→ は上位語、[inst] はインスタンスの上位語):
--   90000001 実体
--   ├ 90000002 動物
--   │ └ 90000010 (日本語の見出し語なし。中間の概念)
--   │   ├ 90000011 猫・ネコ ← 90000020 三毛猫(兄弟が自分だけ)
--   │   ├ 90000012 犬
--   │   ├ 90000013 キツネ
--   │   ├ 90000014 禁止語(除外リストで見出し語が無くなる)
--   │   └ 90000015 未登録語(読みが決まらない)
--   ├ 90000003 物
--   │ ├ 90000030 東京(上位語が2つ: 90000003 と [inst] 90000031)
--   │ ├ 90000040 猫(猫の2つ目の語義。頻度が90000011と同点)
--   │ └ 90000041 犬(犬の2つ目の語義。頻度が90000012より大きい)
--   └ 90000031 (日本語の見出し語なし)
--     └ [inst] 90000032 ル・コルビュジエ

CREATE TABLE word (wordid integer primary key, lang text, lemma text, pron text, pos text);
CREATE TABLE sense (synset text, wordid integer, lang text, rank text, lexid integer, freq integer, src text);
CREATE TABLE synset (synset text, pos text, name text, src text);
CREATE TABLE synlink (synset1 text, synset2 text, link text, src text);
CREATE TABLE synset_def (synset text, lang text, def text, sid text);

INSERT INTO synset VALUES
  ('90000001-n', 'n', 'entity', 'eng30'),
  ('90000002-n', 'n', 'animal', 'eng30'),
  ('90000003-n', 'n', 'thing', 'eng30'),
  ('90000010-n', 'n', 'carnivore', 'eng30'),
  ('90000011-n', 'n', 'cat', 'eng30'),
  ('90000012-n', 'n', 'dog', 'eng30'),
  ('90000013-n', 'n', 'fox', 'eng30'),
  ('90000014-n', 'n', 'banned', 'eng30'),
  ('90000015-n', 'n', 'unknown', 'eng30'),
  ('90000020-n', 'n', 'calico', 'eng30'),
  ('90000030-n', 'n', 'tokyo', 'eng30'),
  ('90000031-n', 'n', 'architect', 'eng30'),
  ('90000032-n', 'n', 'le_corbusier', 'eng30'),
  ('90000040-n', 'n', 'cat2', 'eng30'),
  ('90000041-n', 'n', 'hound', 'eng30'),
  ('90000099-v', 'v', 'run', 'eng30');

INSERT INTO synlink VALUES
  ('90000002-n', '90000001-n', 'hype', 'eng30'),
  ('90000001-n', '90000002-n', 'hypo', 'eng30'),
  ('90000003-n', '90000001-n', 'hype', 'eng30'),
  ('90000010-n', '90000002-n', 'hype', 'eng30'),
  ('90000011-n', '90000010-n', 'hype', 'eng30'),
  ('90000012-n', '90000010-n', 'hype', 'eng30'),
  ('90000013-n', '90000010-n', 'hype', 'eng30'),
  ('90000014-n', '90000010-n', 'hype', 'eng30'),
  ('90000015-n', '90000010-n', 'hype', 'eng30'),
  ('90000020-n', '90000011-n', 'hype', 'eng30'),
  ('90000030-n', '90000031-n', 'inst', 'eng30'),
  ('90000030-n', '90000003-n', 'hype', 'eng30'),
  ('90000031-n', '90000001-n', 'hype', 'eng30'),
  ('90000032-n', '90000031-n', 'inst', 'eng30'),
  ('90000031-n', '90000032-n', 'hasi', 'eng30'),
  ('90000040-n', '90000003-n', 'hype', 'eng30'),
  ('90000041-n', '90000003-n', 'hype', 'eng30');

INSERT INTO word VALUES
  (1, 'jpn', '実体', NULL, 'n'),
  (2, 'jpn', '動物', NULL, 'n'),
  (3, 'jpn', '物', NULL, 'n'),
  (4, 'jpn', '猫', NULL, 'n'),
  (5, 'jpn', 'ネコ', NULL, 'n'),
  (6, 'jpn', '犬', NULL, 'n'),
  (7, 'jpn', 'キツネ', NULL, 'n'),
  (8, 'jpn', '禁止語', NULL, 'n'),
  (9, 'jpn', '未登録語', NULL, 'n'),
  (10, 'jpn', '三毛猫', NULL, 'n'),
  (11, 'jpn', '東京', NULL, 'n'),
  (12, 'jpn', 'ル・コルビュジエ', NULL, 'n'),
  (13, 'jpn', '走る', NULL, 'v'),
  (101, 'eng', 'cat', NULL, 'n'),
  (102, 'eng', 'kitty', NULL, 'n'),
  (103, 'eng', 'dog', NULL, 'n'),
  (104, 'eng', 'hound', NULL, 'n'),
  (105, 'eng', 'cat2', NULL, 'n'),
  (106, 'eng', 'fox', NULL, 'n');

INSERT INTO sense VALUES
  ('90000001-n', 1, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000002-n', 2, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000003-n', 3, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000011-n', 4, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000040-n', 4, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000011-n', 5, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000012-n', 6, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000041-n', 6, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000013-n', 7, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000014-n', 8, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000015-n', 9, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000020-n', 10, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000030-n', 11, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000032-n', 12, 'jpn', NULL, NULL, NULL, 'hand'),
  ('90000099-v', 13, 'jpn', NULL, NULL, NULL, 'hand'),
  -- 同じ語義の行が重なっていても1つの語義として扱う
  ('90000001-n', 1, 'jpn', NULL, NULL, NULL, 'mono'),
  -- 英語の語義の頻度。概念ごとに合計する(90000011 は 3 + 2 = 5 で 90000040 と同点)
  ('90000011-n', 101, 'eng', '0', 1, 3, 'eng-30'),
  ('90000011-n', 102, 'eng', '0', 1, 2, 'eng-30'),
  ('90000040-n', 105, 'eng', '0', 1, 5, 'eng-30'),
  ('90000012-n', 103, 'eng', '0', 1, 2, 'eng-30'),
  ('90000041-n', 104, 'eng', '0', 1, 9, 'eng-30'),
  ('90000013-n', 106, 'eng', '0', 1, NULL, 'eng-30');

INSERT INTO synset_def VALUES
  ('90000011-n', 'jpn', '家で飼われる', '1'),
  ('90000011-n', 'jpn', 'ネコ科の動物', '0'),
  ('90000011-n', 'eng', 'pet', '1'),
  ('90000011-n', 'eng', 'feline', '0'),
  -- 本物と同じく、同じ sid に複数の版がある(同じ文の繰り返し、例文付き)。最も短い版を使う
  ('90000011-n', 'eng', 'pet', '1'),
  ('90000011-n', 'eng', 'feline; "the cat sat on the mat"', '0'),
  ('90000011-n', 'img', 'cat.png', '0'),
  ('90000012-n', 'jpn', 'イヌ科の動物', '0'),
  ('90000012-n', 'jpn', 'イヌ科の動物', '1'),  -- 別の sid に同じ文(1回だけつなぐ)
  ('90000012-n', 'eng', '   ', '0');
