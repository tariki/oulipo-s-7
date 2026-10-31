import type { ApiClient } from '../api/ApiClient';
import type { ApiErrorCode } from '../api/ApiError';
import type { AnalyticsEvent, TransformEvent } from '../api/types';

/**
 * 匿名のアクセス解析のイベントを送る(機能設計書「アクセス解析(匿名)」)。
 * 送信の失敗は利用者に表示せず、再送もしない(変換の操作を妨げないため)。
 * 本文や語は送らない(イベントの型に入る項目だけを送る)。
 */
export function trackEvent(client: ApiClient, event: AnalyticsEvent): void {
  client.postEvent(event).catch(() => undefined);
}

/** ページを開いたときに作る64ビットのランダム値(16桁の16進数)。メモリ上だけに持つ。 */
export function createPageViewId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** 文字数の区分(1,000以下 / 10,000以下 / 50,000以下)。 */
export function charsBucketOf(chars: number): 'le1000' | 'le10000' | 'le50000' {
  if (chars <= 1_000) {
    return 'le1000';
  }
  return chars <= 10_000 ? 'le10000' : 'le50000';
}

/** 解析のイベントに入れるエラーコード(想定外の応答は INTERNAL_ERROR として数える)。 */
export function toEventErrorCode(code: ApiErrorCode): NonNullable<TransformEvent['errorCode']> {
  return code === 'UNEXPECTED_RESPONSE' ? 'INTERNAL_ERROR' : code;
}
