#!/usr/bin/env bash
# プルリクエストを出す前の確認をまとめて実行する。最初の失敗で止まる。
# 内容は docs/development-guidelines.md「手元で確かめることとCI」の手元の列。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

step() {
  printf '\n==> %s\n' "$1"
}

# --locked: uv.lock が pyproject.toml と合っていなければ、書き換えずに失敗する(CIの uv sync --locked と同じ)
py() {
  uv run --locked --directory "$ROOT/server" "$@"
}

web() {
  npm --prefix "$ROOT/web" run --silent "$@"
}

step "Python: ruff check"
py ruff check
step "Python: ruff format --check"
py ruff format --check
step "Python: mypy"
py mypy
step "Python: tools/analysis・scripts の ruff check・format --check"
py ruff check ../tools/analysis ../scripts
py ruff format --check ../tools/analysis ../scripts
step "Python: lint-imports"
py lint-imports
step "Python: pytest(カバレッジ 全体80%以上)"
py pytest --cov --cov-report=term --cov-fail-under=80
step "Python: カバレッジ services/・s7builder/ それぞれ90%以上"
py coverage report --include='src/s7/services/*' --fail-under=90
py coverage report --include='src/s7builder/*' --fail-under=90

step "画面: lint"
web lint
step "画面: format:check"
web format:check
step "画面: typecheck"
web typecheck
step "画面: test(カバレッジ80%以上)"
web coverage
step "画面: build"
web build

step "シェルスクリプト: ShellCheck"
shellcheck "$ROOT"/scripts/*.sh "$ROOT"/.devcontainer/*.sh

printf '\nすべての確認が通りました。\n'
