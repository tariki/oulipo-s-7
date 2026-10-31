import { ApiError } from './ApiError';
import type {
  AnalyticsEvent,
  ErrorCode,
  MetaResponse,
  TransformRequest,
  TransformResponse,
} from './types';

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

/** 画面からの呼び出しであることを示す(KPIの集計で画面とそれ以外を分けるため。認証ではない)。 */
const CLIENT_HEADERS = { 'X-S7-Client': 'web' } as const;

/** 応答を待つ上限。応答が返らない通信で、画面が変換中のまま止まらないようにする。 */
export const REQUEST_TIMEOUT_MS = 60_000;

/** APIのエラーコード(機能設計書「エラーレスポンスの形式」)。知らないコードは想定外の応答として扱う。 */
const KNOWN_ERROR_CODES: ReadonlySet<string> = new Set<ErrorCode>([
  'TEXT_EMPTY',
  'TEXT_TOO_LONG',
  'INVALID_MODE',
  'INVALID_N',
  'INVALID_REQUEST',
  'LEMMA_NOT_FOUND',
  'PAYLOAD_TOO_LARGE',
  'RATE_LIMITED',
  'SERVICE_STARTING',
  'INTERNAL_ERROR',
]);

/**
 * /api/v1/* の呼び出しを1か所にまとめる。部品から直接 fetch を呼ばない。
 * エラーレスポンス・通信の失敗・想定外の応答は ApiError にして投げる。
 */
export class ApiClient {
  private readonly fetchImpl: FetchLike;

  constructor(fetchImpl: FetchLike = (input, init) => fetch(input, init)) {
    this.fetchImpl = fetchImpl;
  }

  async getMeta(): Promise<MetaResponse> {
    const body = await this.requestJson('/api/v1/meta', { method: 'GET' });
    if (!hasStringField(body, 'dictionaryVersion')) {
      throw new ApiError('UNEXPECTED_RESPONSE');
    }
    return body as MetaResponse;
  }

  async transform(request: TransformRequest): Promise<TransformResponse> {
    const body = await this.requestJson('/api/v1/transform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    // 描画で落ちないよう、最低限の形を確かめる(中身はサーバーの型を信じる)
    if (!hasStringField(body, 'text') || !('segments' in body) || !Array.isArray(body.segments)) {
      throw new ApiError('UNEXPECTED_RESPONSE');
    }
    return body as TransformResponse;
  }

  /** 解析のイベントを送る。成功は 204(本文なし)。 */
  async postEvent(event: AnalyticsEvent): Promise<void> {
    await this.send('/api/v1/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    });
  }

  private async requestJson(path: string, init: RequestInit): Promise<unknown> {
    const response = await this.send(path, init);
    try {
      return (await response.json()) as unknown;
    } catch {
      throw new ApiError('UNEXPECTED_RESPONSE', { status: response.status });
    }
  }

  private async send(path: string, init: RequestInit): Promise<Response> {
    let response: Response;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, REQUEST_TIMEOUT_MS);
    try {
      response = await this.fetchImpl(path, {
        ...init,
        headers: { ...CLIENT_HEADERS, ...(init.headers as Record<string, string> | undefined) },
        signal: controller.signal,
      });
    } catch {
      // 通信の失敗と、時間切れによる中止
      throw new ApiError('NETWORK_ERROR');
    } finally {
      clearTimeout(timer);
    }
    if (!response.ok) {
      throw await toApiError(response);
    }
    return response;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const retryAfterSeconds = parseRetryAfter(response.headers.get('Retry-After'));
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // 本文がJSONでない応答(前段のプロキシのエラーなど)
  }
  if (!isErrorResponse(body)) {
    return new ApiError('UNEXPECTED_RESPONSE', { status: response.status });
  }
  return new ApiError(body.error.code, {
    status: response.status,
    message: body.error.message,
    ...(retryAfterSeconds === null ? {} : { retryAfterSeconds }),
  });
}

function parseRetryAfter(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value)) {
    return null;
  }
  return Number(value);
}

function isErrorResponse(value: unknown): value is { error: { code: ErrorCode; message: string } } {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false;
  }
  const { error } = value;
  return (
    hasStringField(error, 'code') &&
    KNOWN_ERROR_CODES.has(error.code) &&
    hasStringField(error, 'message')
  );
}

function hasStringField<K extends string>(
  value: unknown,
  key: K,
): value is Record<K, string> & Record<string, unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    key in value &&
    typeof (value as Record<string, unknown>)[key] === 'string'
  );
}
