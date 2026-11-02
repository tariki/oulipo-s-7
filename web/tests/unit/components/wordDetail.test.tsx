import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { NounSegment } from '../../../src/api/types';
import type { SensePickerState } from '../../../src/components/SensePicker';
import { WordDetail } from '../../../src/components/WordDetail';
import { SENSES } from '../support/fakeApi';

const REPLACED: NounSegment = {
  type: 'noun',
  nounIndex: 0,
  original: '猫',
  replaced: '虎',
  status: 'replaced',
  lemma: '猫',
  synsetId: '02121620-n',
  route: {
    type: 'concept',
    climbs: [],
    parent: { synsetId: '1-n', lemma: '動物', definition: null },
    from: { synsetId: '02121620-n', lemma: '猫', definition: null },
    to: { synsetId: '2-n', lemma: '虎', definition: null },
    groupSize: 3,
    wrapped: false,
  },
};

const LOADED: SensePickerState = { status: 'success', senses: SENSES.senses };

function renderDetail(overrides: Partial<Parameters<typeof WordDetail>[0]> = {}) {
  const headingRef = createRef<HTMLHeadingElement>();
  const props = {
    segment: REPLACED,
    mode: 'concept' as const,
    senses: LOADED,
    overriddenSynsetId: undefined,
    isBusy: false,
    headingRef,
    onToggleExclusion: vi.fn(),
    onSelectSense: vi.fn(),
    onRetrySenses: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  };
  render(<WordDetail {...props} />);
  return { ...props, headingRef };
}

describe('WordDetail', () => {
  it('選んだ語と状態の説明、経路、置き換えない指定、語義の一覧を出す', () => {
    const props = renderDetail();

    expect(screen.getByRole('region', { name: '選んだ語: 猫 → 虎' })).toBeInTheDocument();
    expect(screen.getByText('元の語: 猫')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '置き換えの経路' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'この語は置き換えない' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '猫・ネコネコ科の動物' })).toBeChecked();
    expect(props.headingRef.current).toHaveTextContent('選んだ語: 猫 → 虎');
  });

  it('置き換えない指定を切り替える。変換中は受け付けない', async () => {
    const user = userEvent.setup();
    const busy = renderDetail({ isBusy: true });
    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));
    expect(busy.onToggleExclusion).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'この語は置き換えない' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });

  it('置き換えない指定の語は、指定を外すボタンだけを出す(経路と語義は出さない)', async () => {
    const user = userEvent.setup();
    const props = renderDetail({
      segment: { ...REPLACED, status: 'excluded', replaced: '猫', route: null },
    });

    expect(screen.getByRole('region', { name: '選んだ語: 猫' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '置き換えの経路' })).not.toBeInTheDocument();
    expect(screen.queryByRole('group', { name: '語義を選び直す' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '置き換える(指定を外す)' }));
    expect(props.onToggleExclusion).toHaveBeenCalledTimes(1);
  });

  it('五十音順では、語義の選び直しは概念版で使えると書く', () => {
    renderDetail({ mode: 'gojuon', senses: null });

    expect(screen.getByText('語義の選び直しは、概念版で使えます。')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: '語義を選び直す' })).not.toBeInTheDocument();
  });

  it('語義を選ぶと onSelectSense を呼ぶ', async () => {
    const user = userEvent.setup();
    const props = renderDetail();

    await user.click(screen.getByRole('radio', { name: '猫三味線のこと' }));

    expect(props.onSelectSense).toHaveBeenCalledWith('10000001-n');
  });

  it('閉じるボタンと、面の中の Esc で閉じる', async () => {
    const user = userEvent.setup();
    const props = renderDetail();

    await user.click(screen.getByRole('button', { name: '閉じる' }));
    expect(props.onClose).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('radio', { name: '猫三味線のこと' }));
    await user.keyboard('{Escape}');
    expect(props.onClose).toHaveBeenCalledTimes(2);
  });
});
