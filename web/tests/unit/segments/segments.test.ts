import { describe, expect, it } from 'vitest';

import type { NounSegment, Segment } from '../../../src/api/types';
import { joinOriginal, joinReplaced } from '../../../src/segments/joinSegments';
import { splitParagraphs } from '../../../src/segments/splitParagraphs';

function noun(original: string, replaced: string, nounIndex = 0): NounSegment {
  return { type: 'noun', nounIndex, original, replaced, status: 'replaced', lemma: original };
}

function text(value: string): Segment {
  return { type: 'text', text: value };
}

function joinItems(items: (string | NounSegment)[]): string {
  return items.map((i) => (typeof i === 'string' ? i : i.original)).join('');
}

describe('joinSegments', () => {
  it('元の文章と変換後の文章を組み立てる', () => {
    const segments = [text('吾輩は'), noun('猫', '獅子'), text('である。')];

    expect(joinOriginal(segments)).toBe('吾輩は猫である。');
    expect(joinReplaced(segments)).toBe('吾輩は獅子である。');
  });
});

describe('splitParagraphs', () => {
  it('改行ごとに段落に分け、改行は段落の末尾に残す', () => {
    const segments = [text('一行目の'), noun('猫', '犬'), text('\n二行目\n\n三行目')];

    const paragraphs = splitParagraphs(segments);

    expect(paragraphs.map((p) => joinItems(p.items))).toEqual([
      '一行目の猫\n',
      '二行目\n',
      '\n',
      '三行目',
    ]);
    expect(paragraphs.map((p) => p.index)).toEqual([0, 1, 2, 3]);
  });

  it('長い段落は、上限を超える前の句点の直後で分ける', () => {
    const segments = [text('あいう。えお。'), noun('猫', '犬'), text('かき。')];

    const paragraphs = splitParagraphs(segments, 6);

    expect(paragraphs.map((p) => joinItems(p.items))).toEqual(['あいう。', 'えお。', '猫かき。']);
  });

  it('句点が無ければ上限を超えても分けない(名詞も分けない)', () => {
    const paragraphs = splitParagraphs([text('あいうえおかきくけこ'), noun('猫', '犬')], 3);

    expect(paragraphs).toHaveLength(1);
  });

  it('つなげると元の文章に戻る', () => {
    const segments = [text('a。\nb'), noun('猫', '犬'), text('。c\n'), noun('犬', '猫', 1)];

    const joined = splitParagraphs(segments, 2)
      .map((p) => joinItems(p.items))
      .join('');

    expect(joined).toBe(joinOriginal(segments));
  });

  it('空の区切りからは段落を作らない', () => {
    expect(splitParagraphs([])).toEqual([]);
  });
});

describe('splitParagraphs(長文)', () => {
  it('改行の無い長文も2,000文字前後のまとまりに分ける', () => {
    const sentence = 'あいうえおかきくけ。';
    const segments = Array.from({ length: 5_000 }, (_, i) =>
      i % 2 === 0 ? text(sentence) : noun('猫', '犬', i),
    );

    const paragraphs = splitParagraphs(segments);

    expect(paragraphs.length).toBeGreaterThanOrEqual(14); // 約27,500文字
    for (const paragraph of paragraphs) {
      expect(joinItems(paragraph.items).length).toBeLessThanOrEqual(2_000);
    }
  });
});
