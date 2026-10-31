import { describe, expect, it, vi } from 'vitest';

import { ApiClient, REQUEST_TIMEOUT_MS } from '../../../src/api/ApiClient';
import { ApiError } from '../../../src/api/ApiError';

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

async function catchError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) {
      return error;
    }
    throw error;
  }
  throw new Error('例外になりませんでした');
}

describe('ApiClient', () => {
  it('すべてのリクエストに X-S7-Client: web を付ける', async () => {
    const fetchMock = vi.fn((path: string) =>
      Promise.resolve(
        jsonResponse(
          path === '/api/v1/meta'
            ? { dictionaryVersion: '1' }
            : { text: '猫', segments: [], meta: {} },
        ),
      ),
    );
    const client = new ApiClient(fetchMock);

    await client.getMeta();
    await client.transform({ text: '猫', mode: 'gojuon', n: 7 });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/meta',
      expect.objectContaining({ method: 'GET', headers: { 'X-S7-Client': 'web' } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/transform',
      expect.objectContaining({
        method: 'POST',
        headers: { 'X-S7-Client': 'web', 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: '猫', mode: 'gojuon', n: 7 }),
      }),
    );
  });

  it('応答が返らなければ時間切れで中止し、NETWORK_ERROR にする', async () => {
    vi.useFakeTimers();
    try {
      const fetchMock = vi.fn(
        (_: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () => {
              reject(new DOMException('aborted', 'AbortError'));
            });
          }),
      );
      const client = new ApiClient(fetchMock);

      const pending = catchError(client.getMeta());
      await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);

      expect((await pending).code).toBe('NETWORK_ERROR');
    } finally {
      vi.useRealTimers();
    }
  });

  it.each([
    ['meta', (c: ApiClient) => c.getMeta(), { version: 1 }],
    [
      'transform',
      (c: ApiClient) => c.transform({ text: '猫', mode: 'gojuon', n: 7 }),
      { text: '猫' },
    ],
  ])('%s の応答の形が違えば UNEXPECTED_RESPONSE にする', async (_, call, body) => {
    const client = new ApiClient(vi.fn().mockResolvedValue(jsonResponse(body)));

    expect((await catchError(call(client))).code).toBe('UNEXPECTED_RESPONSE');
  });

  it('知らないエラーコードは UNEXPECTED_RESPONSE にする', async () => {
    const client = new ApiClient(
      vi
        .fn()
        .mockResolvedValue(jsonResponse({ error: { code: 'SOMETHING_NEW', message: 'x' } }, 400)),
    );

    expect((await catchError(client.getMeta())).code).toBe('UNEXPECTED_RESPONSE');
  });

  it('エラーレスポンスをコード・メッセージ・Retry-After つきの ApiError にする', async () => {
    const client = new ApiClient(
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'RATE_LIMITED', message: '混み合っています' } }, 429, {
          'Retry-After': '12',
        }),
      ),
    );

    const error = await catchError(client.transform({ text: '猫', mode: 'gojuon', n: 7 }));

    expect(error.code).toBe('RATE_LIMITED');
    expect(error.status).toBe(429);
    expect(error.serverMessage).toBe('混み合っています');
    expect(error.retryAfterSeconds).toBe(12);
  });

  it('通信の失敗を NETWORK_ERROR にする', async () => {
    const client = new ApiClient(vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const error = await catchError(client.getMeta());

    expect(error.code).toBe('NETWORK_ERROR');
    expect(error.status).toBeNull();
  });

  it.each([
    ['JSONでないエラー', new Response('<html>Bad Gateway</html>', { status: 502 })],
    ['形の違うエラー', jsonResponse({ detail: 'Not Found' }, 404)],
  ])('%s は UNEXPECTED_RESPONSE にする', async (_, response) => {
    const client = new ApiClient(vi.fn().mockResolvedValue(response));

    const error = await catchError(client.getMeta());

    expect(error.code).toBe('UNEXPECTED_RESPONSE');
    expect(error.retryAfterSeconds).toBeNull();
  });

  it('成功の応答がJSONでなければ UNEXPECTED_RESPONSE にする', async () => {
    const client = new ApiClient(vi.fn().mockResolvedValue(new Response('ok', { status: 200 })));

    expect((await catchError(client.getMeta())).code).toBe('UNEXPECTED_RESPONSE');
  });

  it('数字でない Retry-After は無視する', async () => {
    const client = new ApiClient(
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'SERVICE_STARTING', message: '準備中' } }, 503, {
          'Retry-After': 'soon',
        }),
      ),
    );

    expect((await catchError(client.getMeta())).retryAfterSeconds).toBeNull();
  });

  it('イベントを送る(204)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    const client = new ApiClient(fetchMock);

    await client.postEvent({ event: 'page_view', pageViewId: '0123456789abcdef' });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/events',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

describe('ApiError.from', () => {
  it('ApiError はそのまま、それ以外は UNEXPECTED_RESPONSE にする', () => {
    const original = new ApiError('NETWORK_ERROR');

    expect(ApiError.from(original)).toBe(original);
    expect(ApiError.from(new Error('内部の情報')).code).toBe('UNEXPECTED_RESPONSE');
    expect(ApiError.from('文字列').code).toBe('UNEXPECTED_RESPONSE');
  });
});
