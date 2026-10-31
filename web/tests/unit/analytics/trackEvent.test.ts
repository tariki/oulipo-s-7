import { describe, expect, it, vi } from 'vitest';

import { charsBucketOf, createPageViewId, trackEvent } from '../../../src/analytics/trackEvent';
import type { ApiClient } from '../../../src/api/ApiClient';

describe('trackEvent', () => {
  it('イベントを送り、送信の失敗は無視する', async () => {
    const postEvent = vi.fn().mockRejectedValue(new Error('offline'));
    const client = { postEvent } as unknown as ApiClient;

    trackEvent(client, { event: 'copy', pageViewId: '0123456789abcdef', transformSeq: 1 });
    await Promise.resolve();

    expect(postEvent).toHaveBeenCalledWith({
      event: 'copy',
      pageViewId: '0123456789abcdef',
      transformSeq: 1,
    });
  });
});

describe('createPageViewId', () => {
  it('16桁の16進数を作る', () => {
    expect(createPageViewId()).toMatch(/^[0-9a-f]{16}$/);
  });
});

describe('charsBucketOf', () => {
  it.each([
    [1, 'le1000'],
    [1_000, 'le1000'],
    [1_001, 'le10000'],
    [10_000, 'le10000'],
    [10_001, 'le50000'],
    [50_000, 'le50000'],
  ])('%i文字は %s', (chars, bucket) => {
    expect(charsBucketOf(chars)).toBe(bucket);
  });
});
