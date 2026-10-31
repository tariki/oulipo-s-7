#!/usr/bin/env bash
# 変換用辞書(data/build/s7dict.sqlite)とビルドの報告(data/reports/build-report.json)を作る。
# 先に scripts/fetch-wordnet.sh で日本語WordNetを取得しておく。
# 品質の報告(s7builder quality)は、変換の処理ができてからここに足す。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

uv run --locked --directory "$ROOT/server" python -m s7builder build "$@"
