import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { App } from '../../src/App';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App', () => {
  it('/ で変換画面を表示する', () => {
    renderAt('/');
    expect(screen.getByRole('heading', { level: 1, name: 'S+7メーカー' })).toBeInTheDocument();
  });

  it('/about で「このアプリについて」を表示する', () => {
    renderAt('/about');
    expect(
      screen.getByRole('heading', { level: 1, name: 'このアプリについて' }),
    ).toBeInTheDocument();
  });

  it('リンクで2つの画面を行き来できる', async () => {
    const user = userEvent.setup();
    renderAt('/');

    await user.click(screen.getByRole('link', { name: 'このアプリについて' }));
    expect(
      screen.getByRole('heading', { level: 1, name: 'このアプリについて' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: '変換画面へ戻る' }));
    expect(screen.getByRole('heading', { level: 1, name: 'S+7メーカー' })).toBeInTheDocument();
  });
});
