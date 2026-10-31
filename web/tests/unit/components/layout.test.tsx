import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { Panel } from '../../../src/components/Panel';
import { SiteHeader } from '../../../src/components/SiteHeader';
import { Wordmark } from '../../../src/components/Wordmark';

describe('Wordmark', () => {
  it('「S+7」の絵は「S+7メーカー」と読み上げる', () => {
    render(<Wordmark />);

    expect(screen.getByRole('img', { name: 'S+7メーカー' })).toBeInTheDocument();
  });
});

describe('SiteHeader', () => {
  function renderAt(path: string, isPageHeading = path === '/') {
    render(
      <MemoryRouter initialEntries={[path]}>
        <SiteHeader isPageHeading={isPageHeading} />
      </MemoryRouter>,
    );
  }

  it('変換画面では「S+7」が h1「S+7メーカー」で、変換画面へのリンクになる', () => {
    renderAt('/');

    const heading = screen.getByRole('heading', { level: 1, name: 'S+7メーカー' });
    expect(within(heading).getByRole('link')).toHaveAttribute('href', '/');
  });

  it('ほかのページでは「S+7」を見出しにしない(ページ名を h1 にするため)', () => {
    renderAt('/about');

    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'S+7メーカー' })).toHaveAttribute('href', '/');
  });

  it('メニューに変換画面・このアプリについて・API を置き、今のページに印を付ける', () => {
    renderAt('/about');

    const nav = screen.getByRole('navigation', { name: 'ページ' });
    expect(within(nav).getByRole('link', { name: '変換する' })).toHaveAttribute('href', '/');
    expect(within(nav).getByRole('link', { name: 'このアプリについて' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(nav).getByRole('link', { name: 'API' })).toHaveAttribute('href', '/api/docs');
  });

  it('アプリの一言の説明を表示する', () => {
    renderAt('/');

    expect(screen.getByText(/文章の名詞を、辞書でN個先の名詞に置き換える/)).toBeInTheDocument();
  });
});

describe('Panel', () => {
  it('見出しを名前にした section で、中身と右上に置くものを表示する', () => {
    render(
      <Panel title="変換後" tone="replaced" actions={<button type="button">コピー</button>}>
        <p>本文</p>
      </Panel>,
    );

    const region = screen.getByRole('region', { name: '変換後' });
    expect(within(region).getByRole('heading', { level: 2, name: '変換後' })).toBeInTheDocument();
    expect(within(region).getByRole('button', { name: 'コピー' })).toBeInTheDocument();
    expect(within(region).getByText('本文')).toBeInTheDocument();
  });

  it('置き場所の class を足せる', () => {
    render(
      <Panel title="原文" tone="original" className="extra">
        <p>本文</p>
      </Panel>,
    );

    expect(screen.getByRole('region', { name: '原文' })).toHaveClass('extra');
  });
});
