import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../src/api/ApiError';
import type { TransformResponse } from '../../../src/api/types';
import {
  SLOW_THRESHOLD_MS,
  type SettledTransform,
  useTransform,
} from '../../../src/hooks/useTransform';
import { createFakeApi, starting, transformResponse } from '../support/fakeApi';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

async function settle() {
  await act(() => vi.advanceTimersByTimeAsync(0));
}

function setup(api = createFakeApi()) {
  const settled: SettledTransform[] = [];
  const hook = renderHook(() => useTransform(api.client, (s) => settled.push(s)));
  return { api, settled, ...hook };
}

describe('useTransform', () => {
  it('確認中 → 入力待ち → 変換中 → 結果表示', async () => {
    const { api, result, settled } = setup();
    expect(result.current.state.status).toBe('checking');
    await settle();
    expect(result.current.state).toEqual({ status: 'idle' });

    act(() => {
      result.current.setText('吾輩は猫である。');
      result.current.setMode('concept');
      result.current.setN(3);
    });
    act(() => {
      result.current.submit();
    });
    expect(result.current.state.status).toBe('loading');
    await settle();

    expect(api.transform).toHaveBeenCalledWith({ text: '吾輩は猫である。', mode: 'concept', n: 3 });
    expect(result.current.state.status).toBe('success');
    expect(settled).toEqual([
      expect.objectContaining({
        ok: true,
        request: { text: '吾輩は猫である。', mode: 'concept', n: 3 },
      }),
    ]);
  });

  it('変換が1秒を超えたら isSlow になる', async () => {
    const api = createFakeApi();
    let resolve: (value: TransformResponse) => void = () => undefined;
    api.transform.mockImplementation(() => new Promise((r) => (resolve = r)));
    const { result } = setup(api);
    await settle();
    act(() => {
      result.current.setText('猫');
      result.current.submit();
    });

    await act(() => vi.advanceTimersByTimeAsync(SLOW_THRESHOLD_MS - 1));
    expect(result.current.isSlow).toBe(false);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(result.current.isSlow).toBe(true);

    await act(async () => {
      resolve(transformResponse('猫'));
      await Promise.resolve();
    });
    expect(result.current.isSlow).toBe(false);
  });

  it('変換中にもう一度押しても送らない(二重送信の防止)', async () => {
    const { api, result } = setup();
    await settle();
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
      result.current.submit();
    });
    await settle();

    expect(api.transform).toHaveBeenCalledTimes(1);
  });

  it('確認中に押した操作を保持し、準備ができ次第変換する', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValueOnce(starting());
    const { result } = setup(api);
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    expect(result.current.hasPendingRequest).toBe(true);
    await settle();
    expect(result.current.state.status).toBe('starting');
    expect(api.transform).not.toHaveBeenCalled();

    await act(() => vi.advanceTimersByTimeAsync(1_000));

    expect(api.transform).toHaveBeenCalledWith({ text: '猫', mode: 'gojuon', n: 7 });
    expect(result.current.hasPendingRequest).toBe(false);
    expect(result.current.state.status).toBe('success');
  });

  it('待っている間に入力を変えたら、保持した操作を捨てる', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValueOnce(starting());
    const { result } = setup(api);
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    act(() => {
      result.current.setN(8);
    });
    expect(result.current.hasPendingRequest).toBe(false);

    await act(() => vi.advanceTimersByTimeAsync(2_000));

    expect(api.transform).not.toHaveBeenCalled();
    expect(result.current.state.status).toBe('idle');
  });

  it('20秒たっても準備できなければ、保持した操作を捨てて失敗にする', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(starting());
    const { result, settled } = setup(api);
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });

    await act(() => vi.advanceTimersByTimeAsync(20_000));

    expect(result.current.state.status).toBe('error');
    expect(result.current.hasPendingRequest).toBe(false);
    expect(settled).toEqual([expect.objectContaining({ ok: false })]);
    expect(api.transform).not.toHaveBeenCalled();
  });

  it('変換が503なら準備中に戻り、準備ができたら同じ操作をやり直す', async () => {
    const api = createFakeApi();
    api.transform.mockRejectedValueOnce(starting());
    const { result, settled } = setup(api);
    await settle();
    api.getMeta.mockRejectedValueOnce(starting());
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    await settle();
    expect(result.current.state.status).toBe('starting');
    expect(settled).toEqual([]); // 再試行の間は数えない

    await act(() => vi.advanceTimersByTimeAsync(2_000));

    expect(api.transform).toHaveBeenCalledTimes(2);
    expect(result.current.state.status).toBe('success');
    expect(settled).toHaveLength(1);
  });

  it('失敗しても入力は残る', async () => {
    const api = createFakeApi();
    api.transform.mockRejectedValueOnce(new ApiError('INTERNAL_ERROR', { status: 500 }));
    const { result, settled } = setup(api);
    await settle();
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    await settle();

    expect(result.current.state.status).toBe('error');
    expect(result.current.text).toBe('猫');
    expect(settled).toEqual([expect.objectContaining({ ok: false })]);
  });

  it('結果の表示中に文章を編集したら、古い結果を薄く残して入力待ちに戻る', async () => {
    const { result } = setup();
    await settle();
    act(() => {
      result.current.setText('吾輩は猫である。');
    });
    act(() => {
      result.current.submit();
    });
    await settle();

    act(() => {
      result.current.setText('吾輩は犬である。');
    });

    expect(result.current.state).toEqual({
      status: 'idle',
      staleResult: transformResponse('吾輩は猫である。'),
    });
  });

  it('変換中に文章が変わったら、届いた結果を古いものとして扱う', async () => {
    const { result } = setup();
    await settle();
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
      result.current.setText('犬');
    });
    await settle();

    expect(result.current.state).toEqual({ status: 'idle', staleResult: transformResponse('猫') });
  });

  it('meta の確認に失敗したら失敗を表示し、押せば変換を試す', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(new ApiError('NETWORK_ERROR'));
    const { result } = setup(api);
    await settle();
    expect(result.current.state.status).toBe('error');

    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    await settle();

    expect(result.current.state.status).toBe('success');
  });
});

describe('useTransform(検証の指摘への対応)', () => {
  it('時間切れの後に押すと、変換のリクエストを送る', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(starting());
    const { result } = setup(api);
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(result.current.readiness.status).toBe('timedOut');

    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    await settle();

    expect(api.transform).toHaveBeenCalledTimes(1);
    expect(result.current.state.status).toBe('success');
  });

  it('時間切れの後に文章を編集したら、エラーの表示を消して入力待ちに戻る', async () => {
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(starting());
    const { result } = setup(api);
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(result.current.state.status).toBe('error');

    act(() => {
      result.current.setText('猫');
    });

    expect(result.current.state.status).toBe('idle');
  });

  it('変換中に入力を変えてから503が返ったら、古い操作を保持しない', async () => {
    const api = createFakeApi();
    let reject: (error: unknown) => void = () => undefined;
    api.transform.mockImplementationOnce(() => new Promise((_, r) => (reject = r)));
    const { result } = setup(api);
    await settle();
    act(() => {
      result.current.setText('猫');
    });
    act(() => {
      result.current.submit();
    });
    act(() => {
      result.current.setN(9);
    });

    api.getMeta.mockRejectedValueOnce(starting());
    await act(async () => {
      reject(starting());
      await Promise.resolve();
    });
    await act(() => vi.advanceTimersByTimeAsync(3_000));

    expect(result.current.hasPendingRequest).toBe(false);
    expect(api.transform).toHaveBeenCalledTimes(1); // n=7 の操作を送り直さない
  });

  it('変換し直している間も、直前の結果を残す', async () => {
    const api = createFakeApi();
    const { result } = setup(api);
    await settle();
    act(() => {
      result.current.setText('吾輩は猫である。');
    });
    act(() => {
      result.current.submit();
    });
    await settle();
    api.transform.mockImplementationOnce(() => new Promise(() => undefined));

    act(() => {
      result.current.setMode('concept');
    });
    act(() => {
      result.current.submit();
    });

    expect(result.current.state).toEqual({
      status: 'loading',
      previousResult: transformResponse('吾輩は猫である。'),
    });
  });
});
