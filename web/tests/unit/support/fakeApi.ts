import { vi } from 'vitest';

import type { ApiClient } from '../../../src/api/ApiClient';
import { ApiError } from '../../../src/api/ApiError';
import type {
  AnalyticsEvent,
  MetaResponse,
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
}

/** ApiClient の偽物。既定では meta も変換も成功する。 */
export function createFakeApi(): FakeApi {
  const getMeta = vi.fn<() => Promise<MetaResponse>>(() => Promise.resolve(META));
  const transform = vi.fn<(request: TransformRequest) => Promise<TransformResponse>>((request) =>
    Promise.resolve(transformResponse(request.text)),
  );
  const postEvent = vi.fn<(event: AnalyticsEvent) => Promise<void>>(() => Promise.resolve());
  const client = { getMeta, transform, postEvent } as unknown as ApiClient;
  return { client, getMeta, transform, postEvent };
}
