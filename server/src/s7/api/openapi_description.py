"""API仕様書(/api/docs)の全体の説明(機能設計書「API仕様書」)。"""

from typing import Final

from s7.domain import limits

DESCRIPTION: Final = f"""
文章中の名詞を、辞書の中でN個先の語に置き換えるAPIです(OuLiPoのS+7)。

- 利用規約: [/about#api-terms](/about#api-terms)
- 辞書データの出典とライセンス: [/about#credits](/about#credits)(応答の `meta.attribution` にも入れます)
- 辞書バージョンの更新履歴: [/about#dictionary-history](/about#dictionary-history)

## 入力の型

型の自動変換はしません。`n` に `"7"`・`7.0`・`true` を送ると400になります。

| 項目 | 受け付ける値 |
|------|--------------|
| `text` | 1〜{limits.MAX_CHARS:,}文字の文字列(Unicodeのコードポイント数)。空白だけの文字列、単独のサロゲートを含む文字列は400 |
| `mode` | `gojuon`(五十音順S+N)、`concept`(概念版S+N) |
| `n` | JSONの整数 {limits.N_MIN}〜{limits.N_MAX}。省略時は{limits.DEFAULT_N} |
| `exclusions` | 0以上の整数の配列。{limits.MAX_EXCLUSIONS:,}個まで |
| `senseOverrides` | キーは10進の整数の文字列、値は概念ID(`^[0-9]{{8}}-n$`)。{limits.MAX_SENSE_OVERRIDES:,}個まで |

本文は1MBまでです。

## エラーコード

エラーは `{{"error": {{"code": ..., "message": ..., "details": ...}}}}` の形で返します。

| コード | HTTP | 条件 |
|--------|------|------|
| `TEXT_EMPTY` | 400 | `text` が空、または空白類だけ |
| `TEXT_TOO_LONG` | 400 | {limits.MAX_CHARS:,}文字を超える |
| `INVALID_MODE` | 400 | `mode` が `gojuon`・`concept` 以外 |
| `INVALID_N` | 400 | `n` が{limits.N_MIN}〜{limits.N_MAX}のJSONの整数でない |
| `INVALID_REQUEST` | 400 | JSONの形式が不正、型が違う、単独のサロゲートを含む、指定の形式や個数が不正 |
| `PAYLOAD_TOO_LARGE` | 413 | 本文が1MBを超える |
| `RATE_LIMITED` | 429 | 利用制限を超えた |
| `LEMMA_NOT_FOUND` | 404 | 語義の一覧で、見出し語が辞書に無い |
| `SERVICE_STARTING` | 503 | 起動中(辞書の読み込み中) |
| `INTERNAL_ERROR` | 500 | 想定外のエラー |

## 利用制限

接続元ごとに、直近60秒間で数えます。

| 枠 | 対象 | 上限 |
|----|------|------|
| 変換など | `/api/v1/transform`、`/api/v1/senses` | {limits.TRANSFORM_REQUESTS_PER_MINUTE}回/分 |
| 画面の補助 | `/api/v1/meta`、`/api/v1/events` | {limits.AUXILIARY_REQUESTS_PER_MINUTE}回/分 |
| 文字数 | `/api/v1/transform` の `text` の合計 | {limits.CHARS_PER_MINUTE:,}文字/分 |

429を受けたら、`Retry-After` ヘッダーの秒数だけ待ってから再試行してください。

## 起動中の503

サーバーの起動直後は辞書を読み込むため、数秒間 503(`SERVICE_STARTING`)を返します。
`Retry-After` ヘッダーの秒数だけ待ってから再試行してください。

## 互換性の方針

`/api/v1` のまま、次の変更を行うことがあります。利用者のプログラムは、知らない項目を無視してください。

- レスポンスへの項目の追加
- リクエストへの省略できる項目の追加
- エンドポイントの追加

項目の削除・名前や意味の変更、既存のリクエストへの応答で新しい値(`status`、エラーコードなど)を返すことは、
`/api/v2` で行います。サーバーは、リクエストの知らない項目を無視します。
"""
