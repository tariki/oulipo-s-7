import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { ConceptRoute, GojuonRoute } from '../../../src/api/types';
import { RoutePanel } from '../../../src/components/RoutePanel';

function gojuon(neighbors: string[], neighborsOmitted = 0, wrapped = false): GojuonRoute {
  return { type: 'gojuon', fromIndex: 10, toIndex: 17, wrapped, neighbors, neighborsOmitted };
}

const CAT = { synsetId: '02121620-n', lemma: '猫', definition: 'ネコ科の動物' };
const ANIMAL = { synsetId: '00015388-n', lemma: '動物', definition: null };
const NAMELESS = { synsetId: '00000001-n', lemma: null, definition: '英語の定義' };
const TIGER = { synsetId: '02129604-n', lemma: '虎', definition: '大型のネコ科の動物' };

describe('RoutePanel(五十音順)', () => {
  it('元の語、間の語、変換後の語を順に並べる', () => {
    render(<RoutePanel route={gojuon(['猫科', '猫背'])} original="猫" replaced="根こそぎ" />);

    const items = within(screen.getByRole('list')).getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual([
      '猫(元の語)',
      '猫科',
      '猫背',
      '根こそぎ(変換後の語)',
    ]);
    expect(screen.queryByText(/先頭に戻りました/)).not.toBeInTheDocument();
  });

  it('省いた語の数を3語目と4語目の間に出し、末尾から戻ったことを書く', () => {
    render(
      <RoutePanel
        route={gojuon(['a', 'b', 'c', 'x', 'y', 'z'], 1_234, true)}
        original="猫"
        replaced="根こそぎ"
      />,
    );

    const items = within(screen.getByRole('list')).getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual([
      '猫(元の語)',
      'a',
      'b',
      'c',
      '…(1,234語省略)',
      'x',
      'y',
      'z',
      '根こそぎ(変換後の語)',
    ]);
    expect(screen.getByText('辞書の末尾を超えたため、先頭に戻りました。')).toBeInTheDocument();
  });
});

describe('RoutePanel(概念版)', () => {
  const route: ConceptRoute = {
    type: 'concept',
    climbs: [],
    parent: ANIMAL,
    from: CAT,
    to: TIGER,
    groupSize: 12,
    wrapped: false,
  };

  it('上位語、元の概念、変換後の概念と定義文を出す', () => {
    render(<RoutePanel route={route} original="猫" replaced="虎" />);

    expect(screen.getByText('兄弟の概念の共通の上位語').nextSibling).toHaveTextContent('動物');
    expect(screen.getByText('元の概念').nextSibling).toHaveTextContent('猫ネコ科の動物');
    expect(screen.getByText('変換後の概念(兄弟12個の中で進んだ先)').nextSibling).toHaveTextContent(
      '虎大型のネコ科の動物',
    );
    expect(screen.queryByText(/階層を上がりました/)).not.toBeInTheDocument();
  });

  it('階層を上がった経路を関係の種類つきで出す。日本語の見出し語の無い概念も示す', () => {
    render(
      <RoutePanel
        route={{
          ...route,
          climbs: [
            { from: CAT, to: NAMELESS, relation: 'hypernym' },
            { from: NAMELESS, to: ANIMAL, relation: 'instance_hypernym' },
          ],
          wrapped: true,
        }}
        original="猫"
        replaced="虎"
      />,
    );

    const steps = within(screen.getByRole('list')).getAllByRole('listitem');
    expect(steps.map((step) => step.textContent)).toEqual([
      '猫→ 上位語 →(日本語の見出し語なし)英語の定義',
      '(日本語の見出し語なし)→ インスタンスの上位語 →動物',
    ]);
    expect(screen.getByText('上がった先の概念')).toBeInTheDocument();
    expect(
      screen.getByText('兄弟の概念の末尾を超えたため、先頭に戻りました。'),
    ).toBeInTheDocument();
  });
});
