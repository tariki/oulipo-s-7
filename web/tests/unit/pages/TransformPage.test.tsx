import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { ApiError } from '../../../src/api/ApiError';
import { ApiClientProvider } from '../../../src/hooks/apiClientContext';
import { errorMessage } from '../../../src/pages/messages';
import { TransformPage } from '../../../src/pages/TransformPage';
import { type FakeApi, createFakeApi, transformResponse } from '../support/fakeApi';

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

describe('TransformPage(選んだ語の面、P1)', () => {
  /** 除外と語義の指定に応じた結果を返す偽の変換(概念版なら synsetId を返す)。 */
  function withSpecs(api: FakeApi) {
    api.transform.mockImplementation((request) => {
      const response = transformResponse(request.text);
      const isExcluded = request.exclusions?.includes(0) ?? false;
      const synsetId = request.senseOverrides?.['0'] ?? '02121620-n';
      return Promise.resolve({
        ...response,
        segments: response.segments.map((segment) =>
          segment.type !== 'noun'
            ? segment
            : isExcluded
              ? { ...segment, status: 'excluded' as const, replaced: segment.original }
              : {
                  ...segment,
                  replaced: synsetId === '10000001-n' ? '三味線' : '獅子',
                  ...(request.mode === 'concept' ? { synsetId } : {}),
                },
        ),
        meta: { ...response.meta, mode: request.mode },
      });
    });
    return api;
  }

  async function transformed(mode: '五十音順' | '概念版' = '五十音順') {
    const user = userEvent.setup();
    const api = renderPage(withSpecs(createFakeApi()));
    await user.type(screen.getByLabelText('文章'), '吾輩は猫である。');
    await user.click(screen.getByRole('radio', { name: mode }));
    await user.click(screen.getByRole('button', { name: '変換する' }));
    await screen.findByRole('button', { name: /元の語は猫/ });
    return { user, api };
  }

  it('語を選ぶと面を開いて見出しにフォーカスし、Esc で閉じて語にフォーカスを戻す', async () => {
    const { user } = await transformed();
    const token = screen.getByRole('button', { name: '獅子、元の語は猫' });

    await user.click(token);
    const heading = screen.getByRole('heading', { name: '選んだ語: 猫 → 獅子' });
    expect(heading).toHaveFocus();
    expect(screen.getByText('語義の選び直しは、概念版で使えます。')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('heading', { name: /選んだ語/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '獅子、元の語は猫' })).toHaveFocus();
  });

  it('置き換えない指定をすると変換し直し、元の語に戻る。外すと置き換わる', async () => {
    const { user, api } = await transformed();
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));

    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));

    expect(await screen.findByRole('button', { name: '猫、置き換えない指定' })).toBeInTheDocument();
    expect(api.transform).toHaveBeenLastCalledWith({
      text: '吾輩は猫である。',
      mode: 'gojuon',
      n: 7,
      exclusions: [0],
    });
    await user.click(screen.getByRole('button', { name: '置き換える(指定を外す)' }));
    expect(await screen.findByRole('button', { name: '獅子、元の語は猫' })).toBeInTheDocument();
  });

  it('概念版で語義を選び直すと、その語義で変換し直す', async () => {
    const { user, api } = await transformed('概念版');
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));

    const other = await screen.findByRole('radio', { name: '猫三味線のこと' });
    expect(screen.getByRole('radio', { name: '猫・ネコネコ科の動物' })).toBeChecked();
    await user.click(other);

    expect(await screen.findByRole('button', { name: '三味線、元の語は猫' })).toBeInTheDocument();
    expect(api.transform).toHaveBeenLastCalledWith({
      text: '吾輩は猫である。',
      mode: 'concept',
      n: 7,
      senseOverrides: { '0': '10000001-n' },
    });
    expect(api.getSenses).toHaveBeenCalledWith('猫');
    expect(screen.getByRole('radio', { name: '猫三味線のこと' })).toBeChecked();
  });

  it('語義の一覧を取れなければ理由を出し、結果は残す', async () => {
    const { user, api } = await transformed('概念版');
    api.getSenses.mockRejectedValueOnce(new ApiError('LEMMA_NOT_FOUND', { status: 404 }));
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));

    expect(await screen.findByText('この語の語義は辞書にありません')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '獅子、元の語は猫' })).toBeInTheDocument();
  });

  it('変換し直している間に Esc を押しても、語にフォーカスを戻す', async () => {
    const { user, api } = await transformed();
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));
    api.transform.mockImplementationOnce(() => new Promise(() => undefined));

    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('heading', { name: /選んだ語/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '獅子、元の語は猫' })).toHaveFocus();
  });

  it('変換し直している間に Esc で閉じたら、新しい結果の語にもフォーカスを戻す', async () => {
    const { user, api } = await transformed();
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));
    let finish: (() => void) | undefined;
    const pending = api.transform.getMockImplementation();
    api.transform.mockImplementationOnce(
      (request) =>
        new Promise((resolve) => {
          finish = () => {
            void pending?.(request).then(resolve);
          };
        }),
    );
    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));
    await user.keyboard('{Escape}');

    finish?.();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '猫、置き換えない指定' })).toHaveFocus();
    });
  });

  it('変換に失敗したら面を閉じ、次に成功しても面は開かない', async () => {
    const { user, api } = await transformed();
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));
    api.transform.mockRejectedValueOnce(new ApiError('INTERNAL_ERROR', { status: 500 }));

    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /選んだ語/ })).not.toBeInTheDocument();

    // 指定は残っているため、次の変換は置き換えない指定つきになる
    await user.click(screen.getByRole('button', { name: '変換する' }));
    await screen.findByRole('button', { name: '猫、置き換えない指定' });
    expect(screen.queryByRole('heading', { name: /選んだ語/ })).not.toBeInTheDocument();
  });

  it('本文を編集したら面を閉じ、指定を消す', async () => {
    const { user, api } = await transformed();
    await user.click(screen.getByRole('button', { name: '獅子、元の語は猫' }));
    await user.click(screen.getByRole('button', { name: 'この語は置き換えない' }));
    await screen.findByRole('button', { name: '猫、置き換えない指定' });

    await user.type(screen.getByLabelText('文章'), '名前はまだ無い。');

    expect(screen.queryByRole('heading', { name: /選んだ語/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '変換する' }));
    await waitFor(() => {
      expect(api.transform).toHaveBeenLastCalledWith({
        text: '吾輩は猫である。名前はまだ無い。',
        mode: 'gojuon',
        n: 7,
      });
    });
  });
});
