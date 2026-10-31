#!/usr/bin/env bash
# 日本語WordNet 1.1(wnjpn.db)をダウンロードし、data/wnjpn.db.sha256 で中身を確かめてから
# data/source/wnjpn.db に置く。すでに正しいファイルがあれば何もしない。
#
# WORDNET_URL: ダウンロード元を変えるとき(配布元が使えなくなり、保管した原本から取る場合など)。
#   中身はどこから取っても同じSHA-256で確かめる。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORDNET_URL="${WORDNET_URL:-https://github.com/bond-lab/wnja/releases/download/v1.1/wnjpn.db.gz}"
DEST="$ROOT/data/source/wnjpn.db"
EXPECTED="$(cut -d ' ' -f 1 "$ROOT/data/wnjpn.db.sha256")"

sha256_of() {
  sha256sum "$1" | cut -d ' ' -f 1
}

if [[ -f "$DEST" && "$(sha256_of "$DEST")" == "$EXPECTED" ]]; then
  echo "日本語WordNetは取得済みです: $DEST"
  exit 0
fi

# 途中で失敗しても壊れたファイルを残さないよう、同じディレクトリの一時ディレクトリで作業する
mkdir -p "$(dirname "$DEST")"
WORK="$(mktemp -d "$(dirname "$DEST")/.fetch-wordnet.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

echo "日本語WordNetをダウンロードします: $WORDNET_URL"
curl --fail --silent --show-error --location --retry 3 --output "$WORK/wnjpn.db.gz" "$WORDNET_URL"
gunzip "$WORK/wnjpn.db.gz"

ACTUAL="$(sha256_of "$WORK/wnjpn.db")"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "SHA-256が一致しません(期待: $EXPECTED、実際: $ACTUAL)" >&2
  exit 1
fi

mv "$WORK/wnjpn.db" "$DEST"
echo "日本語WordNetを置きました: $DEST"
