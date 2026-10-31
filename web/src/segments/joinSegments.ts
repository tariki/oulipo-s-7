import type { Segment } from '../api/types';

/** 元の文章(文字列と名詞の original を順につなげたもの)。 */
export function joinOriginal(segments: readonly Segment[]): string {
  return segments.map((s) => (s.type === 'text' ? s.text : s.original)).join('');
}

/** 変換後の文章(文字列と名詞の replaced を順につなげたもの)。 */
export function joinReplaced(segments: readonly Segment[]): string {
  return segments.map((s) => (s.type === 'text' ? s.text : s.replaced)).join('');
}
