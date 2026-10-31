import type { NounSegment, Segment } from '../api/types';

/** 段落ごとに描画するための、区切りのまとまり。 */
export interface Paragraph {
  /** 段落の番号(描画の key)。 */
  index: number;
  /** 文字列(改行を含みうる)と名詞の並び。順につなげると元の区切りに戻る。 */
  items: (string | NounSegment)[];
}

/** 1つのまとまりの文字数の目安(機能設計書「長文の表示」)。 */
export const MAX_PARAGRAPH_CHARS = 2_000;

/**
 * 区切りを段落(改行)ごとのまとまりに分ける。2,000文字を超える段落は句点の直後で分ける。
 * 名詞は分けない。改行は段落の末尾に残す(つなげると元の文章に戻るように)。
 */
export function splitParagraphs(
  segments: readonly Segment[],
  maxChars: number = MAX_PARAGRAPH_CHARS,
): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  let items: (string | NounSegment)[] = [];
  let chars = 0;
  // 最後の句点の直後の位置(items の添字)と、そこまでの文字数。句点が無ければ0
  let lastSentenceEnd = 0;
  let charsAtSentenceEnd = 0;

  const close = () => {
    if (items.length > 0) {
      paragraphs.push({ index: paragraphs.length, items });
    }
    items = [];
    chars = 0;
    lastSentenceEnd = 0;
    charsAtSentenceEnd = 0;
  };

  const add = (item: string | NounSegment) => {
    const length = typeof item === 'string' ? item.length : item.original.length;
    // 足すと上限を超えるなら、最後の句点の直後で区切る(句点が無ければ区切らない)
    if (lastSentenceEnd > 0 && chars + length > maxChars) {
      const rest = items.slice(lastSentenceEnd);
      const restChars = chars - charsAtSentenceEnd;
      items = items.slice(0, lastSentenceEnd);
      close();
      items = rest;
      chars = restChars;
    }
    items.push(item);
    chars += length;
  };

  for (const segment of segments) {
    if (segment.type === 'noun') {
      add(segment);
      continue;
    }
    // 改行と句点の直後で切る(区切り文字は前の部分に残す)
    for (const piece of segment.text.split(/(?<=[\n。])/)) {
      add(piece);
      if (piece.endsWith('\n')) {
        close();
      } else if (piece.endsWith('。')) {
        lastSentenceEnd = items.length;
        charsAtSentenceEnd = chars;
      }
    }
  }
  close();
  return paragraphs;
}
