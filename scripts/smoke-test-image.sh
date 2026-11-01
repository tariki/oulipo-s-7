#!/usr/bin/env bash
# Dockerのイメージを起動し、そのまま公開できる状態かを確かめる。
# CI(.github/workflows/docker.yml)と、Dockerのある手元(ホスト側)で使う。
#
#   docker build -t s7-maker .
#   scripts/smoke-test-image.sh s7-maker
#
# 確かめること: PORT で待ち受けを変えられる、辞書の読み込み後に変換できる、画面に CSP が付く、
# root 以外で動く、実行に要らないもの(日本語WordNet・Node.js・辞書ビルダー・uv)が入っていない、
# イメージが1GB以下(docs/architecture.md「コンテナのビルド」「性能の目標」)。
set -euo pipefail

IMAGE="${1:?使い方: scripts/smoke-test-image.sh <イメージ>}"
HOST_PORT="${SMOKE_TEST_PORT:-18080}"
# ホスティング先が渡す PORT を、既定(8000)と違う値にして確かめる
CONTAINER_PORT=8080
BASE="http://localhost:$HOST_PORT"
READY_TIMEOUT_SECONDS=120
MAX_IMAGE_BYTES=$((1024 * 1024 * 1024))

fail() {
  echo "失敗: $*" >&2
  exit 1
}

container="$(docker run --detach --rm -e PORT="$CONTAINER_PORT" -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE")"
cleanup() {
  local status=$?
  if [[ $status -ne 0 ]]; then
    echo "--- コンテナのログ ---" >&2
    docker logs "$container" >&2 || true
  fi
  docker stop "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "辞書の読み込みを待ちます(最大${READY_TIMEOUT_SECONDS}秒)"
started=$SECONDS
until [[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/meta")" == 200 ]]; do
  if ((SECONDS - started > READY_TIMEOUT_SECONDS)); then
    fail "${READY_TIMEOUT_SECONDS}秒たっても /api/v1/meta が200になりません"
  fi
  sleep 1
done
echo "準備ができました($((SECONDS - started))秒)"

[[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/healthz")" == 200 ]] ||
  fail "/healthz が200ではありません"

replaced="$(curl -s -X POST "$BASE/api/v1/transform" \
  -H 'Content-Type: application/json' \
  -d '{"text":"吾輩は猫である。名前はまだ無い。","mode":"gojuon","n":7}' |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["meta"]["replacedCount"])')"
((replaced > 0)) || fail "変換で名詞が置き換わりません(replacedCount=$replaced)"
echo "変換できました(置き換えた名詞: $replaced)"

headers="$(curl -s -D - -o /dev/null "$BASE/")"
grep -qi '^content-type: text/html' <<<"$headers" || fail "/ が HTML ではありません"
grep -qi '^content-security-policy:' <<<"$headers" || fail "/ に Content-Security-Policy がありません"
echo "画面を配信しています"

[[ "$(docker exec "$container" id -u)" != 0 ]] || fail "root で動いています"

# shellcheck disable=SC2016 # 変数はコンテナの中のシェルで展開する
leftovers="$(docker exec "$container" sh -c '
  for path in /app/data/source/wnjpn.db /app/server/src/s7builder; do
    [ -e "$path" ] && echo "$path"
  done
  for command in node npm uv; do
    command -v "$command"
  done
  true
')"
[[ -z "$leftovers" ]] || fail "実行に要らないものが入っています: $leftovers"

size="$(docker image inspect --format '{{.Size}}' "$IMAGE")"
((size <= MAX_IMAGE_BYTES)) || fail "イメージが1GBを超えています($size バイト)"
echo "イメージのサイズ: $((size / 1024 / 1024))MB"

echo "すべての確認が通りました"
