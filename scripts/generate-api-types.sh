#!/usr/bin/env bash
# サーバーのOpenAPI仕様から、画面のAPIの型(web/src/api/generated/schema.d.ts)を作る。
# APIを変えたら実行し、結果をコミットする。CIは作り直して差分が無いことを確かめる。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="$ROOT/web/src/api/generated/schema.d.ts"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

uv run --locked --directory "$ROOT/server" python "$ROOT/scripts/export-openapi.py" > "$WORK/openapi.json"
mkdir -p "$(dirname "$OUTPUT")"
npm --prefix "$ROOT/web" exec --no -- openapi-typescript "$WORK/openapi.json" --output "$OUTPUT"
npm --prefix "$ROOT/web" exec --no -- prettier --write "$OUTPUT" > /dev/null
echo "APIの型を作りました: $OUTPUT"
