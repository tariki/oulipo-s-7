import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError } from '../../../src/api/ApiError';
import { ApiClientProvider } from '../../../src/hooks/apiClientContext';
import { useSenses } from '../../../src/hooks/useSenses';
import { SENSES, createFakeApi } from '../support/fakeApi';

function setup(initial: { lemma: string | undefined; version: string }) {
  const api = createFakeApi();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApiClientProvider client={api.client}>{children}</ApiClientProvider>
  );
  const hook = renderHook(({ lemma, version }) => useSenses(lemma, version).state, {
    wrapper,
    initialProps: initial,
  });
  return { api, ...hook };
}

describe('useSenses', () => {
  it('見出し語が無ければ取りに行かない', () => {
    const { api, result } = setup({ lemma: undefined, version: '1' });

    expect(result.current).toEqual({ status: 'idle' });
    expect(api.getSenses).not.toHaveBeenCalled();
  });

  it('語義の一覧を取り、同じ語を選び直しても取り直さない', async () => {
    const { api, result, rerender } = setup({ lemma: '猫', version: '1' });
    expect(result.current.status).toBe('loading');

    await waitFor(() => {
      expect(result.current).toEqual({ status: 'success', senses: SENSES.senses });
    });
    rerender({ lemma: undefined, version: '1' });
    rerender({ lemma: '猫', version: '1' });

    expect(result.current.status).toBe('success');
    expect(api.getSenses).toHaveBeenCalledTimes(1);
  });

  it('辞書の版が変わったら取り直す', async () => {
    const { api, result, rerender } = setup({ lemma: '猫', version: '1' });
    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    rerender({ lemma: '猫', version: '2' });

    await waitFor(() => {
      expect(api.getSenses).toHaveBeenCalledTimes(2);
    });
  });

  it('失敗したら retry で取り直す。取り直している間は前の失敗を出さない', async () => {
    const api = createFakeApi();
    api.getSenses.mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiClientProvider client={api.client}>{children}</ApiClientProvider>
    );
    const { result } = renderHook(() => useSenses('猫', '1'), { wrapper });
    await waitFor(() => {
      expect(result.current.state.status).toBe('error');
    });

    act(() => {
      result.current.retry();
    });

    expect(result.current.state.status).toBe('loading');
    await waitFor(() => {
      expect(result.current.state.status).toBe('success');
    });
    expect(api.getSenses).toHaveBeenCalledTimes(2);
  });

  it('失敗したら理由を返し、語を選び直すと取り直す', async () => {
    const { api, result, rerender } = setup({ lemma: undefined, version: '1' });
    api.getSenses.mockRejectedValueOnce(new ApiError('LEMMA_NOT_FOUND', { status: 404 }));

    rerender({ lemma: '猫', version: '1' });
    await waitFor(() => {
      expect(result.current.status).toBe('error');
    });
    expect(result.current).toMatchObject({ error: { code: 'LEMMA_NOT_FOUND' } });

    rerender({ lemma: undefined, version: '1' });
    rerender({ lemma: '猫', version: '1' });
    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });
    expect(api.getSenses).toHaveBeenCalledTimes(2);
  });
});
