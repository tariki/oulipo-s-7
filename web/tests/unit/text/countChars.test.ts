import { describe, expect, it } from 'vitest';

import { countChars } from '../../../src/text/countChars';

describe('countChars', () => {
  it('空文字は0文字', () => {
    expect(countChars('')).toBe(0);
  });

  it('ASCIIと日本語は1文字ずつ数える', () => {
    expect(countChars('abc')).toBe(3);
    expect(countChars('吾輩は猫である')).toBe(7);
  });

  it('絵文字(サロゲートペア)を1文字として数える', () => {
    expect(countChars('猫🐈')).toBe(2);
  });

  it('結合文字はコードポイントごとに数える(Pythonの len() と同じ)', () => {
    // 「か」(U+304B)+ 濁点の結合文字(U+3099)。エディタがNFCに正規化して「が」1文字に
    // 変えないよう、エスケープで書く
    expect(countChars('\u304B\u3099')).toBe(2);
  });
});
