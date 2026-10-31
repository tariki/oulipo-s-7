import { describe, expect, it } from 'vitest';

import { parseDictionaryHistory } from '../../../src/about/parseDictionaryHistory';
import { DICTIONARY_HISTORY, LICENSE_TEXTS } from '../../../src/about/sources';

describe('parseDictionaryHistory', () => {
  it('見出しと箇条書きだけを読む', () => {
    const text = [
      '# 見出し1は無視',
      '## 2026.11.0(2026-11-20)',
      '- 除外する語を追加',
      '- 照合規則を修正',
      '本文は無視',
      '',
      '## 2026.10.0(2026-10-31)',
      '- 初版',
    ].join('\n');

    expect(parseDictionaryHistory(text)).toEqual([
      { version: '2026.11.0', date: '2026-11-20', changes: ['除外する語を追加', '照合規則を修正'] },
      { version: '2026.10.0', date: '2026-10-31', changes: ['初版'] },
    ]);
  });

  it('見出しの前の箇条書きは無視する', () => {
    expect(parseDictionaryHistory('- 孤立した項目\n')).toEqual([]);
  });

  it('リポジトリの更新履歴を読める', () => {
    const releases = parseDictionaryHistory(DICTIONARY_HISTORY);

    expect(releases.at(-1)?.changes).toContain('初版');
  });
});

describe('sources', () => {
  it('ライセンス文を読み込む', () => {
    expect(LICENSE_TEXTS.find((l) => l.title === '日本語WordNet 1.1')?.text).toContain(
      'Japanese WordNet',
    );
    expect(LICENSE_TEXTS.every((l) => l.text.length > 0)).toBe(true);
  });
});
