import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SensePicker } from '../../../src/components/SensePicker';
import { SENSES } from '../support/fakeApi';

describe('SensePicker', () => {
  it('語義ごとに見出し語と定義文を出し、いまの語義を選んだ状態にする', () => {
    render(
      <SensePicker
        state={{ status: 'success', senses: SENSES.senses }}
        selectedSynsetId="02121620-n"
        isBusy={false}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole('group', { name: '語義を選び直す' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '猫・ネコネコ科の動物' })).toBeChecked();
    expect(screen.getByRole('radio', { name: '猫三味線のこと' })).not.toBeChecked();
  });

  it('別の語義を選ぶと onSelect を呼ぶ。変換中は呼ばない', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { rerender } = render(
      <SensePicker
        state={{ status: 'success', senses: SENSES.senses }}
        selectedSynsetId="02121620-n"
        isBusy
        onSelect={onSelect}
        onRetry={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('radio', { name: '猫三味線のこと' }));
    expect(onSelect).not.toHaveBeenCalled();

    rerender(
      <SensePicker
        state={{ status: 'success', senses: SENSES.senses }}
        selectedSynsetId="02121620-n"
        isBusy={false}
        onSelect={onSelect}
        onRetry={vi.fn()}
      />,
    );
    await user.click(screen.getByRole('radio', { name: '猫三味線のこと' }));
    expect(onSelect).toHaveBeenCalledWith('10000001-n');
  });

  it('語義が1つだけなら、そう書く。定義文が無ければ示す', () => {
    render(
      <SensePicker
        state={{
          status: 'success',
          senses: [{ synsetId: '1-n', rank: 0, definition: null, lemmas: ['猫'] }],
        }}
        selectedSynsetId="1-n"
        isBusy={false}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText('この語の語義は1つだけです。')).toBeInTheDocument();
    expect(screen.getByText('(定義文なし)')).toBeInTheDocument();
  });

  it('読み込み中と失敗を表示する', () => {
    const { rerender } = render(
      <SensePicker
        state={{ status: 'loading' }}
        selectedSynsetId={undefined}
        isBusy={false}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('語義の一覧を読み込んでいます…')).toBeInTheDocument();

    rerender(
      <SensePicker
        state={{ status: 'error', message: '語義の一覧を取れませんでした' }}
        selectedSynsetId={undefined}
        isBusy={false}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('語義の一覧を取れませんでした')).toBeInTheDocument();
  });

  it('失敗したら「もう一度読み込む」で取り直せる', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <SensePicker
        state={{ status: 'error', message: '失敗' }}
        selectedSynsetId={undefined}
        isBusy={false}
        onSelect={vi.fn()}
        onRetry={onRetry}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'もう一度読み込む' }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
