import type { ErrorCode } from './types';

/** 画面で扱うエラーの種類。APIのエラーコードに、通信の失敗と想定外の応答を加えたもの。 */
export type ApiErrorCode = ErrorCode | 'NETWORK_ERROR' | 'UNEXPECTED_RESPONSE';

interface ApiErrorOptions {
  status?: number;
  message?: string;
  retryAfterSeconds?: number;
}

/** APIのエラー。エラーレスポンス、通信の失敗、想定外の応答をこの形にそろえる。 */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  /** HTTPステータス。通信の失敗ならnull。 */
  readonly status: number | null;
  /** サーバーが返した利用者向けのメッセージ。無ければnull。 */
  readonly serverMessage: string | null;
  /** Retry-After の秒数。無ければnull。 */
  readonly retryAfterSeconds: number | null;

  constructor(code: ApiErrorCode, options: ApiErrorOptions = {}) {
    super(code);
    this.name = 'ApiError';
    this.code = code;
    this.status = options.status ?? null;
    this.serverMessage = options.message ?? null;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
  }

  /** 想定外の値も含めて ApiError に寄せる(catch した値の中身は表示に使わない)。 */
  static from(error: unknown): ApiError {
    return error instanceof ApiError ? error : new ApiError('UNEXPECTED_RESPONSE');
  }
}
