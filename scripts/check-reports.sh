#!/usr/bin/env bash
# 変換用辞書と2つの報告(build-report.json・quality-report.json)を作り直し、コミット済みのものと
# 一致するかを確かめる。辞書や変換の処理を変えたのに報告を更新し忘れたことを見つける(CIで使う)。
# 先に scripts/fetch-wordnet.sh で日本語WordNetを取得しておく。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORTS=(data/reports/build-report.json data/reports/quality-report.json)

# git diff は未追跡のファイルを比べないため、報告がコミットされていることを先に確かめる
for report in "${REPORTS[@]}"; do
  if ! git -C "$ROOT" cat-file -e "HEAD:$report" 2>/dev/null; then
    echo "報告がコミットされていません: $report" >&2
    exit 1
  fi
done

"$ROOT/scripts/build-dictionary.sh"

# 比べる相手はコミット済みのもの(HEAD)。git add しただけの古い報告では通さない
if ! git -C "$ROOT" diff HEAD --exit-code -- "${REPORTS[@]}"; then
  echo "報告がコミット済みのものと違います。scripts/build-dictionary.sh で作り直してコミットしてください" >&2
  exit 1
fi
echo "報告はコミット済みのものと一致しました"
