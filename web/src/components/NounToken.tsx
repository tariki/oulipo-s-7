import { type KeyboardEvent, useId, useState } from 'react';

import type { NounSegment } from '../api/types';
import styles from './NounToken.module.css';

interface NounTokenProps {
  segment: NounSegment;
  /** 古い結果(文章を編集した後)なら選べなくする。 */
  isSelectable: boolean;
  onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void;
}

interface Appearance {
  className: string | undefined;
  mark: string | null;
  /** 読み上げ名(機能設計書「語の表示」の表)。 */
  label: string;
  /** 選んだときに出す説明。 */
  description: string;
}

function appearanceOf(segment: NounSegment): Appearance {
  const { original, replaced } = segment;
  switch (segment.status) {
    case 'replaced':
      return {
        className: styles.replaced,
        mark: null,
        label: `${replaced}、元の語は${original}`,
        description: `元の語: ${original}`,
      };
    case 'climbed':
      return {
        className: styles.climbed,
        mark: '↑',
        label: `${replaced}、元の語は${original}、上の階層から置き換え`,
        description: `元の語: ${original}(兄弟の概念が無いため、上の階層から置き換え)`,
      };
    case 'no_sibling':
      return {
        className: styles.unchanged,
        mark: '・',
        label: `${original}、置き換えなし、兄弟の概念が無い`,
        description: '置き換えなし: 最上位まで兄弟の概念がありません',
      };
    case 'no_reading':
      return {
        className: styles.unchanged,
        mark: '?',
        label: `${original}、置き換えなし、読みが分からない`,
        description:
          '置き換えなし: 読みが分からないため、五十音順では置き換えません(概念版なら置き換えられます)',
      };
    case 'excluded':
      return {
        className: styles.excluded,
        mark: null,
        label: `${original}、置き換えない指定`,
        description: '置き換えない指定',
      };
    case 'not_in_dictionary':
      return {
        className: styles.notInDictionary,
        mark: null,
        label: original,
        description: '辞書に無い語',
      };
  }
}

/**
 * 変換後の文章の名詞1つ(F4)。色に加えて下線の種類と印で状態を示す。
 * 辞書に無い語以外は button にし、ホバー・フォーカス・選択で元の語と状態の説明を出す。
 */
export function NounToken({ segment, isSelectable, onKeyDown }: NounTokenProps) {
  const tooltipId = useId();
  // フォーカスとクリックで開く。Esc で閉じ、ホバーで出ている表示も消す(WCAG 1.4.13)
  const [isOpen, setIsOpen] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const appearance = appearanceOf(segment);
  const shownText = segment.status === 'excluded' ? segment.original : segment.replaced;
  const mark =
    appearance.mark === null ? null : (
      <span className={styles.mark} aria-hidden="true">
        {appearance.mark}
      </span>
    );

  if (segment.status === 'not_in_dictionary' || !isSelectable) {
    return (
      <span className={appearance.className}>
        {shownText}
        {mark}
      </span>
    );
  }
  return (
    <span
      className={isDismissed ? styles.wrapperDismissed : styles.wrapper}
      onMouseLeave={() => {
        setIsDismissed(false);
      }}
    >
      <button
        type="button"
        className={`${styles.token ?? ''} ${appearance.className ?? ''}`}
        aria-label={appearance.label}
        aria-expanded={isOpen}
        aria-controls={tooltipId}
        tabIndex={-1}
        data-noun-token=""
        onClick={() => {
          // タップでも出す(閉じるのは Esc とフォーカスが外れたとき)
          setIsOpen(true);
          setIsDismissed(false);
        }}
        onFocus={() => {
          setIsOpen(true);
        }}
        onBlur={() => {
          setIsOpen(false);
          setIsDismissed(false);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setIsOpen(false);
            setIsDismissed(true);
            return;
          }
          onKeyDown?.(event);
        }}
      >
        {shownText}
        {mark}
      </button>
      <span id={tooltipId} className={isOpen ? styles.tooltipOpen : styles.tooltip} role="note">
        {appearance.description}
      </span>
    </span>
  );
}
