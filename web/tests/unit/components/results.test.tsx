import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { NounSegment, NounStatus, TransformResponse } from '../../../src/api/types';
import { CopyButton } from '../../../src/components/CopyButton';
import { Legend } from '../../../src/components/Legend';
import { NounToken } from '../../../src/components/NounToken';
import { ResultView } from '../../../src/components/ResultView';
import { SkipLink } from '../../../src/components/SkipLink';
import { transformResponse } from '../support/fakeApi';

function noun(status: NounStatus, replaced = '獅子'): NounSegment {
  return { type: 'noun', nounIndex: 0, original: '猫', replaced, status, lemma: '猫' };
}

describe('NounToken', () => {
  it.each([
    ['replaced', '獅子、元の語は猫', null],
    ['climbed', '獅子、元の語は猫、上の階層から置き換え', '↑'],
    ['no_sibling', '猫、置き換えなし、兄弟の概念が無い', '・'],
    ['no_reading', '猫、置き換えなし、読みが分からない', '?'],
    ['excluded', '猫、置き換えない指定', null],
  ] as const)('%s は button で、読み上げ名は「%s」', (status, label, mark) => {
    const replaced = status === 'no_sibling' || status === 'no_reading' ? '猫' : '獅子';
    render(<NounToken segment={noun(status, replaced)} isSelectable />);

    const button = screen.getByRole('button', { name: label });
    if (mark !== null) {
      // 印は読み上げない(意味は読み上げ名で伝える)
      expect(within(button).getByText(mark)).toHaveAttribute('aria-hidden', 'true');
    }
  });

  it('辞書に無い語は選べない span', () => {
    render(<NounToken segment={noun('not_in_dictionary', '猫')} isSelectable />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByText('猫')).toBeInTheDocument();
  });

  it('除外した語は元の語を表示する', () => {
    render(<NounToken segment={noun('excluded')} isSelectable />);

    expect(screen.getByRole('button')).toHaveTextContent('猫');
  });

  it('選ぶと元の語の説明を開き、Esc で閉じる', async () => {
    const user = userEvent.setup();
    render(<NounToken segment={noun('replaced')} isSelectable />);
    const button = screen.getByRole('button');

    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('note')).toHaveTextContent('元の語: 猫');

    await user.keyboard('{Escape}');
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(button).toHaveFocus();
  });

  it('フォーカスで開き、外れたら閉じる', async () => {
    const user = userEvent.setup();
    render(<NounToken segment={noun('replaced')} isSelectable />);
    const button = screen.getByRole('button');

    button.focus();
    await user.keyboard('{Shift}');
    expect(button).toHaveAttribute('aria-expanded', 'true');

    await user.tab();
    expect(button).toHaveAttribute('aria-expanded', 'false');
  });

  it('古い結果の語は選べない', () => {
    render(<NounToken segment={noun('replaced')} isSelectable={false} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

function resultWith(...nouns: string[]): TransformResponse {
  const base = transformResponse();
  return {
    ...base,
    segments: nouns.flatMap((word, i) => [
      {
        type: 'noun',
        nounIndex: i,
        original: word,
        replaced: `${word}'`,
        status: 'replaced',
        lemma: word,
      },
      { type: 'text', text: 'と' },
    ]),
  };
}

describe('ResultView', () => {
  it('原文と変換後の文章を表示する', () => {
    render(<ResultView id="result" result={transformResponse()} isStale={false} />);

    expect(screen.getByRole('heading', { name: '変換後' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '原文' })).toBeInTheDocument();
    expect(screen.getByText('吾輩は猫である。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '獅子、元の語は猫' })).toBeInTheDocument();
  });

  it('Tab では最初の語に入り、左右の矢印キーで語を移る', async () => {
    const user = userEvent.setup();
    render(<ResultView id="result" result={resultWith('猫', '犬', '鳥')} isStale={false} />);
    const [cat, dog, bird] = screen.getAllByRole('button');

    expect([cat, dog, bird].map((b) => b?.tabIndex)).toEqual([0, -1, -1]);
    await user.tab();
    expect(cat).toHaveFocus();

    await user.keyboard('{ArrowRight}{ArrowRight}');
    expect(bird).toHaveFocus();
    await user.keyboard('{ArrowRight}'); // 末尾では動かない
    expect(bird).toHaveFocus();
    await user.keyboard('{ArrowLeft}');
    expect(dog).toHaveFocus();
    expect([cat, dog, bird].map((b) => b?.tabIndex)).toEqual([-1, 0, -1]);
  });

  it('結果を差し替えても、Tab で入れる語は1つだけ', () => {
    const { rerender } = render(
      <ResultView id="result" result={resultWith('猫', '犬')} isStale={false} />,
    );
    const [, dog] = screen.getAllByRole('button');
    dog?.focus();
    if (dog) {
      dog.tabIndex = 0;
    }

    rerender(<ResultView id="result" result={resultWith('鳥', '魚', '虫')} isStale={false} />);

    const tabStops = screen.getAllByRole('button').filter((b) => b.tabIndex === 0);
    expect(tabStops).toHaveLength(1);
  });

  it('古い結果は語を選べない', () => {
    render(<ResultView id="result" result={transformResponse()} isStale />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('CopyButton', () => {
  it('変換後の文章をコピーし、onCopy を呼ぶ', async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
    const onCopy = vi.fn();
    render(<CopyButton text="吾輩は獅子である。" onCopy={onCopy} />);

    await user.click(screen.getByRole('button', { name: 'コピー' }));

    expect(writeText).toHaveBeenCalledWith('吾輩は獅子である。');
    expect(onCopy).toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent('コピーしました');
  });

  it('コピーできなければ知らせ、onCopy を呼ばない', async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('denied'));
    const onCopy = vi.fn();
    render(<CopyButton text="x" onCopy={onCopy} />);

    await user.click(screen.getByRole('button', { name: 'コピー' }));

    expect(screen.getByRole('status')).toHaveTextContent('コピーできませんでした');
    expect(onCopy).not.toHaveBeenCalled();
  });
});

describe('Legend と SkipLink', () => {
  it('凡例と、結果へのスキップリンクを表示する', () => {
    render(
      <>
        <SkipLink targetId="result" />
        <Legend />
      </>,
    );

    expect(screen.getByRole('link', { name: '結果へ移動' })).toHaveAttribute('href', '#result');
    expect(screen.getByText('辞書に無い語(点線)')).toBeInTheDocument();
  });
});
