#!/usr/bin/env bash
# Dev Containerを作ったときに1回だけ実行する(開発ガイドライン「セットアップ手順」の手順2)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y --no-install-recommends shellcheck

uv sync --directory "$ROOT/server"
npm ci --prefix "$ROOT/web"
# E2Eの設定を入れるまでは e2e:install が無いため、あるときだけ実行する
npm run e2e:install --prefix "$ROOT/web" --if-present
