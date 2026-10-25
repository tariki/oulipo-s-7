#!/usr/bin/env bash
# 開発時に、サーバー(Uvicorn、http://localhost:8000)と画面(Vite、http://localhost:5173)を同時に起動する。
# どちらかが終わったら、もう一方も止める。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 画面の開発サーバーが /api をこのポートへ中継する(web/vite.config.ts)ため、ポートは固定する
API_PORT=8000

# .env があればサーバーに渡す。サーバー自身は .env を読まない
env_args=()
if [[ -f "$ROOT/.env" ]]; then
  env_args=(--env-file "$ROOT/.env")
fi

# npm は子プロセス(vite)にシグナルを渡さないため、同じプロセスグループをまとめて止める
cleanup() {
  trap - EXIT INT TERM
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run --directory "$ROOT/server" "${env_args[@]}" \
  uvicorn --factory s7.app:create_app \
  --host 0.0.0.0 --port "$API_PORT" --no-access-log \
  --reload --reload-dir "$ROOT/server/src" &

npm --prefix "$ROOT/web" run dev -- --host 0.0.0.0 &

# どちらかが終わるまで待つ
wait -n
