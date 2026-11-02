#!/usr/bin/env bash
# 変換用辞書(data/build/s7dict.sqlite)と、2つの報告を作る。
# - ビルドの報告(data/reports/build-report.json)
# - 品質の報告(data/reports/quality-report.json。標準の文章3本での置換率。基準値から5ポイント以上
#   下がった値があれば警告を出す。失敗にはしない)
# 先に scripts/fetch-wordnet.sh で日本語WordNetを取得しておく。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

uv run --locked --directory "$ROOT/server" python -m s7builder build "$@"
uv run --locked --directory "$ROOT/server" python -m s7builder quality
