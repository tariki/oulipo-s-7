import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ModeSelector } from '../../../src/components/ModeSelector';
import { NInput, isValidN } from '../../../src/components/NInput';
import { StatusBanner } from '../../../src/components/StatusBanner';
import { TextInput } from '../../../src/components/TextInput';
import { TransformButton } from '../../../src/components/TransformButton';

describe('TextInput', () => {
  it('文字数をコードポイントで数えて表示する', () => {
    render(<TextInput value="猫🐈" maxChars={10} onChange={vi.fn()} />);

    expect(screen.getByLabelText('文章')).toHaveValue('猫🐈');
    expect(screen.getByText('2 / 10')).toBeInTheDocument();
  });

  it('上限を超えたら知らせる', () => {
    render(<TextInput value={'あ'.repeat(11)} maxChars={10} onChange={vi.fn()} />);

    expect(screen.getByLabelText('文章')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText(/10文字以内で入力してください/)).toBeInTheDocument();
  });

  it('入力を返す', async () => {
    const onChange = vi.fn();
    render(<TextInput value="" maxChars={10} onChange={onChange} />);

    await userEvent.type(screen.getByLabelText('文章'), '猫');

    expect(onChange).toHaveBeenCalledWith('猫');
  });
});

describe('ModeSelector', () => {
  it('ルールを選ぶ', async () => {
    const onChange = vi.fn();
    render(<ModeSelector value="gojuon" onChange={onChange} />);

    expect(screen.getByRole('radio', { name: '五十音順' })).toBeChecked();
    await userEvent.click(screen.getByRole('radio', { name: '概念版' }));

    expect(onChange).toHaveBeenCalledWith('concept');
  });
});

describe('NInput', () => {
  it.each([
    [7, true],
    [1, true],
    [99, true],
    [0, false],
    [100, false],
    [7.5, false],
    [Number.NaN, false],
  ])('%s が有効か: %s', (n, expected) => {
    expect(isValidN(n, 1, 99)).toBe(expected);
  });

  it('範囲外なら知らせる', () => {
    render(<NInput value={100} min={1} max={99} onChange={vi.fn()} />);

    expect(screen.getByRole('alert')).toHaveTextContent('1〜99の整数で入力してください');
    expect(screen.getByLabelText('N')).toHaveAttribute('aria-invalid', 'true');
  });

  it('空にしたら NaN を返す', async () => {
    const onChange = vi.fn();
    render(<NInput value={7} min={1} max={99} onChange={onChange} />);

    await userEvent.clear(screen.getByLabelText('N'));

    expect(onChange).toHaveBeenLastCalledWith(Number.NaN);
  });
});

describe('TransformButton', () => {
  it.each([
    [{ isWaiting: false, isSlow: false }, '変換する'],
    [{ isWaiting: true, isSlow: false }, '準備ができ次第変換します'],
    [{ isWaiting: false, isSlow: true }, '変換中…'],
  ])('%o のときの表示は %s', (props, label) => {
    render(<TransformButton isDisabled={false} isBusy={false} onClick={vi.fn()} {...props} />);

    expect(screen.getByRole('button')).toHaveTextContent(label);
  });

  it('押せないときは押しても呼ばない', async () => {
    const onClick = vi.fn();
    render(
      <TransformButton
        isDisabled
        isBusy={false}
        isWaiting={false}
        isSlow={false}
        onClick={onClick}
      />,
    );

    await userEvent.click(screen.getByRole('button'));

    expect(onClick).not.toHaveBeenCalled();
  });
});

describe('StatusBanner', () => {
  it('エラーは alert で読み上げ、それ以外は表示だけ(読み上げは画面の領域が行う)', () => {
    render(
      <>
        <StatusBanner tone="error" message="失敗" />
        <StatusBanner tone="notice" message="準備中" />
      </>,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('失敗');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByText('準備中')).toBeInTheDocument();
  });
});

describe('TransformButton(変換中)', () => {
  it('変換中は aria-disabled にし、押しても呼ばない(フォーカスを失わない)', async () => {
    const onClick = vi.fn();
    render(
      <TransformButton
        isDisabled={false}
        isBusy
        isWaiting={false}
        isSlow={false}
        onClick={onClick}
      />,
    );
    const button = screen.getByRole('button');

    await userEvent.click(button);

    expect(button).toBeEnabled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(onClick).not.toHaveBeenCalled();
  });
});
