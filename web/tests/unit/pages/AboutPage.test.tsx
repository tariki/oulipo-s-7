import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { AboutPage } from '../../../src/pages/AboutPage';

describe('AboutPage', () => {
  it('7つの節がある', () => {
    const { container } = render(
      <MemoryRouter>
        <AboutPage />
      </MemoryRouter>,
    );

    const ids = [
      'about',
      'notes',
      'report',
      'credits',
      'dictionary-history',
      'api-terms',
      'privacy',
    ];
    for (const id of ids) {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    }
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(7);
  });

  it('ライセンスの全文と更新履歴を表示する', () => {
    render(
      <MemoryRouter>
        <AboutPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('日本語WordNet 1.1')).toBeInTheDocument();
    expect(screen.getByText(/Japanese WordNet/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'バージョン 2026.10.0' })).toHaveTextContent('初版');
    expect(screen.getByRole('link', { name: 'GitHubのIssue' })).toHaveAttribute(
      'href',
      expect.stringContaining('template=excluded-word-report.yml') as string,
    );
  });
});
