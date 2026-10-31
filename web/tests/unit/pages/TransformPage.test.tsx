import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { ApiError } from '../../../src/api/ApiError';
import { ApiClientProvider } from '../../../src/hooks/apiClientContext';
import { errorMessage } from '../../../src/pages/messages';
import { TransformPage } from '../../../src/pages/TransformPage';
import { type FakeApi, createFakeApi } from '../support/fakeApi';

function renderPage(api: FakeApi = createFakeApi()) {
  render(
    <ApiClientProvider client={api.client}>
      <MemoryRouter>
        <TransformPage />
      </MemoryRouter>
    </ApiClientProvider>,
  );
  return api;
}

describe('TransformPage', () => {
  it('文章を変換して結果を表示し、解析のイベントを送る', async () => {
    const user = userEvent.setup();
    const api = renderPage();

    await user.type(screen.getByLabelText('文章'), '吾輩は猫である。');
    await user.click(screen.getByRole('radio', { name: '概念版' }));
    await user.click(screen.getByRole('button', { name: '変換する' }));

    expect(await screen.findByRole('button', { name: '獅子、元の語は猫' })).toBeInTheDocument();
    expect(api.transform).toHaveBeenCalledWith({ text: '吾輩は猫である。', mode: 'concept', n: 7 });
    const events = api.postEvent.mock.calls.map((call) => call[0]);
    expect(events[0]).toEqual({
      event: 'page_view',
      pageViewId: expect.stringMatching(/^[0-9a-f]{16}$/) as unknown,
    });
    expect(events[1]).toMatchObject({
      event: 'transform',
      transformSeq: 1,
      mode: 'concept',
      n: 7,
      charsBucket: 'le1000',
      success: true,
      nounCount: 1,
      excludedCount: 0,
      replacedCount: 1,
    });
    // 本文や語はイベントに入れない
    expect(JSON.stringify(events)).not.toContain('猫');
  });

  it('変換の完了を読み上げる', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('文章'), '吾輩は猫である。');
    await user.click(screen.getByRole('button', { name: '変換する' }));

    expect(
      await screen.findByText('変換しました。名詞1個のうち1個を置き換えました'),
    ).toBeInTheDocument();
  });

  it('コピーしたらコピーのイベントを送る', async () => {
    const user = userEvent.setup();
    const api = renderPage();
    await user.type(screen.getByLabelText('文章'), '吾輩は猫である。');
    await user.click(screen.getByRole('button', { name: '変換する' }));
    await screen.findByRole('button', { name: 'コピー' });

    await user.click(screen.getByRole('button', { name: 'コピー' }));

    await waitFor(() => {
      expect(api.postEvent).toHaveBeenLastCalledWith(
        expect.objectContaining({ event: 'copy', transformSeq: 1 }),
      );
    });
  });

  it('空・上限超過・N が範囲外なら変換できない', async () => {
    const user = userEvent.setup();
    renderPage();
    const button = screen.getByRole('button', { name: '変換する' });
    expect(button).toBeDisabled();

    await user.type(screen.getByLabelText('文章'), '猫');
    await waitFor(() => {
      expect(button).toBeEnabled();
    });
    await user.clear(screen.getByLabelText('N'));
    await user.type(screen.getByLabelText('N'), '100');
    expect(button).toBeDisabled();
  });

  it('失敗したらエラーを表示し、入力を残す。失敗のイベントを送る', async () => {
    const user = userEvent.setup();
    const api = createFakeApi();
    api.transform.mockRejectedValue(new ApiError('NETWORK_ERROR'));
    renderPage(api);

    await user.type(screen.getByLabelText('文章'), '猫');
    await user.click(screen.getByRole('button', { name: '変換する' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('通信に失敗しました');
    expect(screen.getByLabelText('文章')).toHaveValue('猫');
    await waitFor(() => {
      expect(api.postEvent).toHaveBeenLastCalledWith(
        expect.objectContaining({ event: 'transform', success: false, errorCode: 'NETWORK_ERROR' }),
      );
    });
  });

  it('結果の表示中に文章を編集したら、古い結果を薄く表示して知らせる', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText('文章'), '吾輩は猫である。');
    await user.click(screen.getByRole('button', { name: '変換する' }));
    await screen.findByRole('button', { name: '獅子、元の語は猫' });

    await user.type(screen.getByLabelText('文章'), '!');

    expect(
      screen.getAllByText('文章が変わりました。変換し直すと結果が更新されます').length,
    ).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: '獅子、元の語は猫' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'コピー' })).not.toBeInTheDocument();
  });

  it('準備中は知らせ、押した変換を保持する', async () => {
    const user = userEvent.setup();
    const api = createFakeApi();
    api.getMeta.mockRejectedValue(new ApiError('SERVICE_STARTING', { retryAfterSeconds: 1 }));
    renderPage(api);

    expect((await screen.findAllByText(/準備中です/)).length).toBeGreaterThan(0);
    await user.type(screen.getByLabelText('文章'), '猫');
    await user.click(screen.getByRole('button', { name: '変換する' }));

    expect(screen.getByRole('button', { name: '準備ができ次第変換します' })).toBeInTheDocument();
    expect(api.transform).not.toHaveBeenCalled();
  });
});

describe('errorMessage', () => {
  it.each([
    [new ApiError('SERVICE_STARTING'), 'サーバーの準備に時間がかかっています'],
    [new ApiError('RATE_LIMITED', { retryAfterSeconds: 12 }), '12秒後にもう一度お試しください'],
    [new ApiError('RATE_LIMITED'), 'しばらくしてからもう一度お試しください'],
    [
      new ApiError('TEXT_TOO_LONG', { message: '文章は50,000文字以内で' }),
      '文章は50,000文字以内で',
    ],
    [new ApiError('INTERNAL_ERROR', { message: '内部の情報' }), '変換に失敗しました'],
    [new ApiError('UNEXPECTED_RESPONSE'), '変換に失敗しました'],
  ])('%s → %s', (error, expected) => {
    expect(errorMessage(error)).toContain(expected);
  });
});
