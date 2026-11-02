import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';

import { type Page, expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

/**
 * 画面の性能テスト(docs/architecture.md「性能の目標」)。「変換する」を押してから、結果の最後の語が
 * DOM に出るまでを測る。10,000文字は2秒、50,000文字は5秒以内(PRDの測定条件のとおり、各20回の
 * 95パーセンタイル。最初の3回は空回しにして数えない)。
 *
 * - サーバーの処理はモックで返す(サーバーの時間は server/tests/performance/ で測る)
 * - 通信は下り10Mbps・往復遅延50msとみなし、gzip で縮めた応答の大きさから待ち時間を足す
 *   (page.route で返した応答には、ブラウザの回線の制限が効かないため)
 * - 文章は標準の文章(data/standard-texts/)を繰り返したもの。漢字の続きを名詞とみなして応答を作る
 *   (実際の結果に近い名詞の密度。本物の辞書では50,000文字で名詞が約5,700個)
 * - PC幅の Chromium だけで、ほかのテストと並べずに1つずつ測る(npm run e2e:performance。
 *   playwright.config.ts の performance)。スマートフォン相当(CPU 4倍減速)は、ホスティング先の決定後に
 *   本番相当の環境で測る
 */

// 記録(trace)は DOM の写しを取るため、時間を大きく伸ばす。性能のテストでは取らない
test.use({ trace: 'off' });

const TEXTS_DIR = join(import.meta.dirname, '../../../data/standard-texts');
const RUNS = 20;
/**
 * 上限に掛ける倍率(環境変数 E2E_PERF_LIMIT_FACTOR。既定1)。CIは速さのばらつきが大きいため2にし、
 * 性能の大きな劣化を見つけるための値にする(サーバーの性能テストの S7_PERF_LIMIT_SECONDS と同じ考え方)。
 */
const LIMIT_FACTOR = Number(process.env.E2E_PERF_LIMIT_FACTOR ?? '1');
if (!(LIMIT_FACTOR >= 1)) {
  throw new Error(
    `E2E_PERF_LIMIT_FACTOR は1以上の数にしてください: ${String(process.env.E2E_PERF_LIMIT_FACTOR)}`,
  );
}
/** 数えない空回しの回数(最初の数回は、描画の準備や JIT のため遅い)。 */
const WARMUP_RUNS = 3;
const DOWNLOAD_BYTES_PER_SECOND = (10 * 1_000_000) / 8;
const ROUND_TRIP_MS = 50;

/** 標準の文章の本文(冒頭の '#' の行と、その直後の空行を除く)。 */
function readStandardTexts(): string {
  return readdirSync(TEXTS_DIR)
    .filter((name) => name.endsWith('.txt'))
    .sort()
    .map((name) => {
      const lines = readFileSync(join(TEXTS_DIR, name), 'utf8').split('\n');
      let start = 0;
      while (start < lines.length && lines[start]?.startsWith('#') === true) {
        start += 1;
      }
      while (start < lines.length && lines[start] === '') {
        start += 1;
      }
      return lines.slice(start).join('\n').trimEnd();
    })
    .join('\n');
}

/** 標準の文章を繰り返して、ちょうど chars 文字(コードポイント数)にする。 */
function textOf(chars: number): string {
  const source = Array.from(readStandardTexts());
  const result: string[] = [];
  while (result.length < chars) {
    result.push(...source.slice(0, chars - result.length));
  }
  return result.join('');
}

/** 漢字の続きを名詞(置き換えた語)とみなした、変換の応答。 */
function responseOf(text: string): { body: string; nounCount: number } {
  const segments: unknown[] = [];
  let nounIndex = 0;
  let last = 0;
  for (const match of text.matchAll(/[一-鿿々]+/gu)) {
    if (match.index > last) {
      segments.push({ type: 'text', text: text.slice(last, match.index) });
    }
    const word = match[0];
    segments.push({
      type: 'noun',
      nounIndex,
      original: word,
      replaced: `${word}替`,
      status: 'replaced',
      lemma: word,
    });
    nounIndex += 1;
    last = match.index + word.length;
  }
  if (last < text.length) {
    segments.push({ type: 'text', text: text.slice(last) });
  }
  const body = JSON.stringify({
    text,
    segments,
    meta: {
      mode: 'gojuon',
      n: 7,
      nounCount: nounIndex,
      excludedCount: 0,
      replacedCount: nounIndex,
      ignoredExclusions: [],
      ignoredSenseOverrides: [],
      dictionaryVersion: '2026.10.0',
      attribution: '出典',
    },
  });
  return { body, nounCount: nounIndex };
}

function percentile95(values: readonly number[]): number {
  const ordered = [...values].sort((a, b) => a - b);
  return ordered[Math.ceil(ordered.length * 0.95) - 1] ?? Number.NaN;
}

/**
 * 変換を1回して、押してから最後の語が出るまでの時間(ミリ秒)。
 * 変換し直している間も直前の結果の語が DOM に残るため、新しい結果が出たこと(コピーのボタンは
 * 新しい結果でだけ出る)を待ってから、最後の語を待つ。
 */
async function measure(page: Page, text: string, lastIndex: number): Promise<number> {
  await page.getByLabel('文章').fill(text);
  const copy = page.getByRole('button', { name: 'コピー' });
  await expect(copy).toHaveCount(0);
  const started = Date.now();
  await page.getByRole('button', { name: '変換する' }).click();
  await copy.waitFor({ state: 'attached' });
  await page.locator(`#result [data-noun-index="${String(lastIndex)}"]`).waitFor({
    state: 'attached',
  });
  return Date.now() - started;
}

for (const [chars, limitMs] of [
  [10_000, 2_000],
  [50_000, 5_000],
] as const) {
  test(`${chars.toLocaleString('ja-JP')}文字の変換が${String(limitMs / 1000)}秒以内に表示される`, async ({
    page,
  }, testInfo) => {
    test.setTimeout(300_000);
    const text = textOf(chars);
    const { body, nounCount } = responseOf(text);
    const transferMs = ROUND_TRIP_MS + (gzipSync(body).length / DOWNLOAD_BYTES_PER_SECOND) * 1_000;
    await mockApi(page);
    // mockApi の変換より後に登録したものが先に使われる
    await page.route('**/api/v1/transform', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, transferMs));
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });
    await page.goto('/');

    const durations: number[] = [];
    for (let i = 0; i < WARMUP_RUNS; i += 1) {
      await page.getByLabel('文章').fill('');
      await measure(page, text, nounCount - 1);
    }
    for (let i = 0; i < RUNS; i += 1) {
      // 毎回、本文を変えたうえで変換する(同じ結果の描き直しを省かせないため)
      await page.getByLabel('文章').fill('');
      durations.push(await measure(page, text, nounCount - 1));
    }

    const p95 = percentile95(durations);
    const limit = limitMs * LIMIT_FACTOR;
    testInfo.annotations.push({
      type: 'performance',
      description: `${String(chars)}文字 名詞${String(nounCount)}個 通信${transferMs.toFixed(0)}ms 測定 ${durations.join(', ')}ms`,
    });
    // 測った値を残す(性能に効く変更のプルリクエストに書くため)
    process.stdout.write(
      `${String(chars)}文字: 名詞${String(nounCount)}個、通信のみなし${transferMs.toFixed(0)}ms、` +
        `測定 ${durations.join(', ')}ms(95パーセンタイル ${String(p95)}ms、上限 ${String(limit)}ms)\n`,
    );
    expect(p95).toBeLessThanOrEqual(limit);
  });
}
