/**
 * 表示に使うエラーの項目(ApiError の一部)。ApiError は api/ApiError.ts にあり、pages/ からは
 * 取り込めない(取り込めるのは api/types.ts だけ)ため、必要な項目だけをここで受け取る。
 */
interface DisplayableError {
  code: string;
  serverMessage: string | null;
  retryAfterSeconds: number | null;
}

/** 入力の不備のエラー(サーバーのメッセージをそのまま見せてよいもの)。 */
const INPUT_ERRORS = new Set([
  'TEXT_EMPTY',
  'TEXT_TOO_LONG',
  'INVALID_MODE',
  'INVALID_N',
  'INVALID_REQUEST',
  'PAYLOAD_TOO_LARGE',
]);

/**
 * エラーの表示の文言(機能設計書「エラーの分類」)。
 * catch した値の中身(内部の情報)は使わず、コードから決める。
 */
export function errorMessage(error: DisplayableError): string {
  switch (error.code) {
    case 'SERVICE_STARTING':
      // 準備中のまま20秒たった
      return 'サーバーの準備に時間がかかっています。しばらくしてからもう一度お試しください';
    case 'RATE_LIMITED':
      return error.retryAfterSeconds === null
        ? '混み合っています。しばらくしてからもう一度お試しください'
        : `混み合っています。${String(error.retryAfterSeconds)}秒後にもう一度お試しください`;
    case 'NETWORK_ERROR':
      return '通信に失敗しました。もう一度お試しください';
    default:
      if (INPUT_ERRORS.has(error.code) && error.serverMessage !== null) {
        return error.serverMessage;
      }
      return '変換に失敗しました。時間をおいてお試しください';
  }
}

/** 語義の一覧([P1: F8])を取れなかったときの文言。 */
export function sensesErrorMessage(error: DisplayableError): string {
  switch (error.code) {
    case 'LEMMA_NOT_FOUND':
      return 'この語の語義は辞書にありません';
    case 'SERVICE_STARTING':
      return 'サーバーの準備中です。少し待ってから、もう一度読み込んでください';
    case 'RATE_LIMITED':
    case 'NETWORK_ERROR':
      return errorMessage(error);
    default:
      return '語義の一覧を取れませんでした。語を選び直してください';
  }
}
