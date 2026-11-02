import type { Page, Route } from '@playwright/test';

/** E2Eで使う語の置き換え(モード → 元の語 → [置換後の語, 状態])。 */
const REPLACEMENTS: Record<string, Record<string, [string, string]>> = {
  gojuon: { 猫: ['獅子', 'replaced'], 名前: ['名字', 'replaced'] },
  concept: { 猫: ['虎', 'climbed'], 名前: ['名称', 'replaced'] },
};

const META = {
  dictionaryVersion: '2026.10.0',
  limits: {
    maxChars: 50_000,
    nMin: 1,
    nMax: 99,
    maxExclusions: 1_000,
    maxSenseOverrides: 1_000,
    transformRequestsPerMinute: 30,
    auxiliaryRequestsPerMinute: 120,
    charsPerMinute: 200_000,
  },
  attribution: '出典',
};

interface TransformBody {
  text: string;
  mode: string;
  n: number;
  exclusions?: number[];
  senseOverrides?: Record<string, string>;
}

/** 「猫」の語義([P1: F8])。2つ目を選ぶと「三味線」に置き換わる。 */
const CAT_SENSES = {
  lemma: '猫',
  senses: [
    { synsetId: '02121620-n', rank: 0, definition: 'ネコ科の動物', lemmas: ['猫', 'ネコ'] },
    { synsetId: '10000001-n', rank: 1, definition: '三味線のこと', lemmas: ['猫'] },
  ],
};

const CONCEPT = (lemma: string, definition: string | null = null) => ({
  synsetId: `0000000${String(lemma.length)}-n`,
  lemma,
  definition,
});

/** 置換経路([P1: F6])。五十音順は間の語2つ、概念版は階層を1段上がった経路。 */
function routeOf(mode: string, original: string, replaced: string): unknown {
  if (mode === 'gojuon') {
    return {
      type: 'gojuon',
      fromIndex: 100,
      toIndex: 103,
      wrapped: false,
      neighbors: [`${original}科`, `${original}背`],
      neighborsOmitted: 0,
    };
  }
  return {
    type: 'concept',
    climbs: [{ from: CONCEPT(original), to: CONCEPT('ネコ科の動物'), relation: 'hypernym' }],
    parent: CONCEPT('動物', '生き物'),
    from: CONCEPT('ネコ科の動物'),
    to: CONCEPT(replaced, `${replaced}の定義`),
    groupSize: 5,
    wrapped: false,
  };
}

/** 文章中の「猫」「名前」を名詞として置き換えた結果を作る(ほかの文字は文字列)。 */
export function fakeTransform(body: TransformBody): unknown {
  const table = REPLACEMENTS[body.mode] ?? {};
  const words = Object.keys(table);
  const segments: unknown[] = [];
  let rest = body.text;
  let nounIndex = 0;
  let replacedText = '';
  while (rest.length > 0) {
    const index = Math.min(...words.map((w) => (rest.includes(w) ? rest.indexOf(w) : Infinity)));
    if (index === Infinity) {
      segments.push({ type: 'text', text: rest });
      replacedText += rest;
      break;
    }
    if (index > 0) {
      segments.push({ type: 'text', text: rest.slice(0, index) });
      replacedText += rest.slice(0, index);
    }
    const word = words.find((w) => rest.startsWith(w, index)) ?? '';
    const synsetId = body.senseOverrides?.[String(nounIndex)] ?? '02121620-n';
    let [replaced, status] = table[word] ?? [word, 'not_in_dictionary'];
    if (word === '猫' && synsetId === '10000001-n' && body.mode === 'concept') {
      [replaced, status] = ['三味線', 'replaced'];
    }
    if (body.exclusions?.includes(nounIndex) === true) {
      [replaced, status] = [word, 'excluded'];
    }
    segments.push({
      type: 'noun',
      nounIndex,
      original: word,
      replaced,
      status,
      lemma: word,
      ...(body.mode === 'concept' ? { synsetId: word === '猫' ? synsetId : '00000099-n' } : {}),
      ...(status === 'excluded' ? {} : { route: routeOf(body.mode, word, replaced) }),
    });
    replacedText += replaced;
    nounIndex += 1;
    rest = rest.slice(index + word.length);
  }
  return {
    text: replacedText,
    segments,
    meta: {
      mode: body.mode,
      n: body.n,
      nounCount: nounIndex,
      excludedCount: 0,
      replacedCount: nounIndex,
      ignoredExclusions: [],
      ignoredSenseOverrides: [],
      dictionaryVersion: '2026.10.0',
      attribution: '出典',
    },
  };
}

export interface MockOptions {
  /** meta に返すステータスの列(使い切ったら200)。例: [503, 503] で2回準備中。 */
  metaStatuses?: number[];
  /** 変換に返すステータス(既定は200)。 */
  transformStatus?: number;
}

export interface MockApi {
  transformRequests: TransformBody[];
  events: Record<string, unknown>[];
  /** meta が準備中を返すのをやめる。 */
  finishStarting: () => void;
}

function json(route: Route, status: number, body: unknown, headers: Record<string, string> = {}) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    headers,
    body: JSON.stringify(body),
  });
}

/** /api/v1/* をモックにする。送られた変換とイベントを記録する。 */
export async function mockApi(page: Page, options: MockOptions = {}): Promise<MockApi> {
  const metaStatuses = [...(options.metaStatuses ?? [])];
  const mock: MockApi = {
    transformRequests: [],
    events: [],
    finishStarting: () => {
      metaStatuses.length = 0;
    },
  };
  await page.route('**/api/v1/meta', (route) => {
    const status = metaStatuses.shift() ?? 200;
    if (status === 503) {
      return json(
        route,
        503,
        { error: { code: 'SERVICE_STARTING', message: '準備中です' } },
        { 'Retry-After': '1' },
      );
    }
    return json(route, 200, META);
  });
  await page.route('**/api/v1/transform', (route) => {
    const body = route.request().postDataJSON() as TransformBody;
    mock.transformRequests.push(body);
    const status = options.transformStatus ?? 200;
    if (status !== 200) {
      return json(route, status, { error: { code: 'INTERNAL_ERROR', message: '失敗' } });
    }
    return json(route, 200, fakeTransform(body));
  });
  await page.route('**/api/v1/senses*', (route) => {
    const lemma = new URL(route.request().url()).searchParams.get('lemma');
    if (lemma !== '猫') {
      return json(route, 404, { error: { code: 'LEMMA_NOT_FOUND', message: '辞書にありません' } });
    }
    return json(route, 200, CAT_SENSES);
  });
  await page.route('**/api/v1/events', (route) => {
    mock.events.push(route.request().postDataJSON() as Record<string, unknown>);
    return route.fulfill({ status: 204 });
  });
  return mock;
}
