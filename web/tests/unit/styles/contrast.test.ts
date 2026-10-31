// @vitest-environment node
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// tokens.css の色の組み合わせが WCAG 2.2 AA のコントラストを満たすことを確かめる
// (色を変えたときに、基準を割ったことに気づけるように)
// テストでは CSS の取り込みが空になるため、ファイルを直接読む(テストは web/ で動かす)
const TOKENS_PATH = resolve(process.cwd(), 'src/styles/tokens.css');

function readColors(): Map<string, string> {
  const colors = new Map<string, string>();
  const pattern = /--(color-[a-z-]+):\s*(#[0-9a-f]{6});/gi;
  for (const [, name, value] of readFileSync(TOKENS_PATH, 'utf8').matchAll(pattern)) {
    if (name !== undefined && value !== undefined) {
      colors.set(name, value);
    }
  }
  return colors;
}

function luminance(hex: string): number {
  const channel = (start: number) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

function contrast(a: string, b: string): number {
  const [x, y] = [luminance(a), luminance(b)];
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

const PANELS = ['input', 'original', 'replaced', 'plain'];

// [前景, 背景, 基準]。文字は4.5、部品の境界とフォーカスの枠は3
const PAIRS: [string, string, number][] = [
  ['color-text', 'color-background', 4.5],
  ['color-text', 'color-ground', 4.5],
  ['color-on-band', 'color-band', 4.5],
  ['color-error', 'color-error-surface', 4.5],
  ['color-error', 'color-ground', 4.5],
  ['color-text', 'color-notice-surface', 4.5],
  ['color-on-primary', 'color-primary', 4.5],
  ['color-on-primary', 'color-disabled', 4.5],
  ['color-text', 'color-replaced', 4.5],
  ['color-text', 'color-climbed', 4.5],
  ['color-focus', 'color-ground', 3],
  ['color-focus-on-band', 'color-band', 3],
  ...PANELS.flatMap((panel): [string, string, number][] => [
    ['color-text', `color-panel-${panel}`, 4.5],
    [`color-panel-${panel}-label`, `color-panel-${panel}`, 4.5],
    [`color-panel-${panel}-label`, 'color-background', 3],
    ['color-focus', `color-panel-${panel}`, 3],
    ['color-error', `color-panel-${panel}`, 4.5],
  ]),
];

describe('tokens.css のコントラスト', () => {
  const colors = readColors();

  it.each(PAIRS)('%s と %s が %f:1 以上', (foreground, background, minimum) => {
    const fg = colors.get(foreground);
    const bg = colors.get(background);
    expect(fg, foreground).toBeDefined();
    expect(bg, background).toBeDefined();
    expect(contrast(fg ?? '', bg ?? '')).toBeGreaterThanOrEqual(minimum);
  });
});
