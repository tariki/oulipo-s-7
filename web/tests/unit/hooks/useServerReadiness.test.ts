import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../src/api/ApiError';
import { useServerReadiness } from '../../../src/hooks/useServerReadiness';
import { META, createFakeApi, starting } from '../support/fakeApi';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useServerReadiness', () => {
  it('meta が成功したら ready', async () => {
    const api = createFakeApi();

    const { result } = renderHook(() => useServerReadiness(api.client));
    expect(result.current.status).toBe('checking');
    await act(() => vi.runAllTimersAsync());

    expect(result.current.status).toBe('ready');
    expect(result.current.meta).toEqual(META);
  });

  it('503 の間は Retry-After ごとに再試行する', async () => {
    const api = createFakeApi();
    api.getMeta
      .mockRejectedValueOnce(starting())
      .mockRejectedValueOnce(new ApiError('SERVICE_STARTING', { retryAfterSeconds: 2 }));
    const statuses: string[] = [];

    const { result } = renderHook(() =>
      useServerReadiness(api.client, (status) => statuses.push(status)),
    );
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(result.current.status).toBe('starting');

    await act(() => vi.advanceTimersByTimeAsync(1_000));
    expect(api.getMeta).toHaveBeenCalledTimes(2);
    await act(() => vi.advanceTimersByTimeAsync(1_999));
    expect(api.getMeta).toHaveBeenCalledTimes(2);
    await act(() => vi.advanceTimersByTimeAsync(1));

    expect(api.getMeta).toHaveBeenCalledTimes(3);
    expect(result.current.status).toBe('ready');
    expect(statuses).toEqual(['starting', 'starting', 'ready']);
  });

  it('画面を開いてから20秒たっても準備できなければ timedOut', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(starting());

    const { result } = renderHook(() => useServerReadiness(api.client));
    await act(() => vi.advanceTimersByTimeAsync(19_999));
    expect(result.current.status).toBe('starting');
    await act(() => vi.advanceTimersByTimeAsync(1));

    expect(result.current.status).toBe('timedOut');
    const calls = api.getMeta.mock.calls.length;
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(api.getMeta).toHaveBeenCalledTimes(calls); // 諦めたら再試行しない
  });

  it('通信の失敗などは failed', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(new ApiError('NETWORK_ERROR'));

    const { result } = renderHook(() => useServerReadiness(api.client));
    await act(() => vi.runAllTimersAsync());

    expect(result.current.status).toBe('failed');
    expect(result.current.error?.code).toBe('NETWORK_ERROR');
  });

  it('markStarting は、その時点から20秒を数え直して再試行する', async () => {
    const api = createFakeApi();
    const { result } = renderHook(() => useServerReadiness(api.client));
    await act(() => vi.runAllTimersAsync());
    api.getMeta.mockRejectedValue(starting());

    // 画面を開いてから30秒後に、変換が503になった
    await act(() => vi.advanceTimersByTimeAsync(30_000));
    act(() => {
      result.current.markStarting(1);
    });
    expect(result.current.status).toBe('starting');
    await act(() => vi.advanceTimersByTimeAsync(19_000));
    expect(result.current.status).toBe('starting');
    await act(() => vi.advanceTimersByTimeAsync(1_000));

    expect(result.current.status).toBe('timedOut');
  });

  it('画面を閉じたら再試行をやめる', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(starting());

    const { unmount } = renderHook(() => useServerReadiness(api.client));
    await act(() => vi.advanceTimersByTimeAsync(0));
    unmount();
    await act(() => vi.advanceTimersByTimeAsync(5_000));

    expect(api.getMeta).toHaveBeenCalledTimes(1);
  });
});
