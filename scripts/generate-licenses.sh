#!/usr/bin/env bash
# 依存ライブラリのライセンス一覧を licenses/generated/ に作る(「このアプリについて」で表示する)。
# - python.txt: サーバーの実行時の依存関係(開発用を除く)
# - web.txt: 画面に含まれるnpmの依存関係(開発用を除く)
# 追加のツールは使わず、インストール済みのパッケージの情報から作る。
# 依存関係を変えたら実行し、結果をコミットする。CIは作り直して差分が無いことを確かめる。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/licenses/generated"
mkdir -p "$OUT"

# Python: uv export で実行時の依存関係の名前を出し、importlib.metadata でライセンスを読む
uv export --locked --directory "$ROOT/server" --no-dev --no-emit-project --no-hashes \
  --format requirements-txt --quiet \
  | uv run --locked --directory "$ROOT/server" python "$ROOT/scripts/list-python-licenses.py" \
  > "$OUT/python.txt"

# npm: 画面に含まれる依存関係(--omit=dev)を、各パッケージの package.json から読む
npm --prefix "$ROOT/web" ls --omit=dev --all --parseable \
  | node "$ROOT/scripts/list-npm-licenses.mjs" "$ROOT/web" \
  > "$OUT/web.txt"

echo "ライセンス一覧を作りました: $OUT"
