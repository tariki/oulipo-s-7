import { vi } from 'vitest';

import type { ApiClient } from '../../../src/api/ApiClient';
import { ApiError } from '../../../src/api/ApiError';
import type {
  AnalyticsEvent,
  MetaResponse,
  SenseListResponse,
  TransformRequest,
  TransformResponse,
} from '../../../src/api/types';

export const META: MetaResponse = {
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

/** 「吾輩は猫である。」を、猫 → 獅子 に置き換えた結果。 */
export function transformResponse(text = '吾輩は猫である。'): TransformResponse {
  return {
    text: text.replace('猫', '獅子'),
    segments: [
      { type: 'text', text: '吾輩は' },
      {
        type: 'noun',
        nounIndex: 0,
        original: '猫',
        replaced: '獅子',
        status: 'replaced',
        lemma: '猫',
      },
      { type: 'text', text: text.slice(4) },
    ],
    meta: {
      mode: 'gojuon',
      n: 7,
      nounCount: 1,
      excludedCount: 0,
      replacedCount: 1,
      ignoredExclusions: [],
      ignoredSenseOverrides: [],
      dictionaryVersion: '2026.10.0',
      attribution: '出典',
    },
  };
}

export const starting = () =>
  new ApiError('SERVICE_STARTING', { status: 503, retryAfterSeconds: 1 });

export interface FakeApi {
  client: ApiClient;
  getMeta: ReturnType<typeof vi.fn<() => Promise<MetaResponse>>>;
  transform: ReturnType<typeof vi.fn<(request: TransformRequest) => Promise<TransformResponse>>>;
  postEvent: ReturnType<typeof vi.fn<(event: AnalyticsEvent) => Promise<void>>>;
  getSenses: ReturnType<typeof vi.fn<(lemma: string) => Promise<SenseListResponse>>>;
}

/** 「猫」の語義2つ。 */
export const SENSES: SenseListResponse = {
  lemma: '猫',
  senses: [
    { synsetId: '02121620-n', rank: 0, definition: 'ネコ科の動物', lemmas: ['猫', 'ネコ'] },
    { synsetId: '10000001-n', rank: 1, definition: '三味線のこと', lemmas: ['猫'] },
  ],
};

/** ApiClient の偽物。既定では meta も変換も成功する。 */
export function createFakeApi(): FakeApi {
  const getMeta = vi.fn<() => Promise<MetaResponse>>(() => Promise.resolve(META));
  const transform = vi.fn<(request: TransformRequest) => Promise<TransformResponse>>((request) =>
    Promise.resolve(transformResponse(request.text)),
  );
  const postEvent = vi.fn<(event: AnalyticsEvent) => Promise<void>>(() => Promise.resolve());
  const getSenses = vi.fn<(lemma: string) => Promise<SenseListResponse>>(() =>
    Promise.resolve(SENSES),
  );
  const client = { getMeta, transform, postEvent, getSenses } as unknown as ApiClient;
  return { client, getMeta, transform, postEvent, getSenses };
}
