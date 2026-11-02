import { type Ref, useEffect, useRef } from 'react';

import type { Mode, NounSegment } from '../api/types';
import { statusDescriptionOf } from './NounToken';
import { RoutePanel } from './RoutePanel';
import { SensePicker, type SensePickerState } from './SensePicker';
import styles from './WordDetail.module.css';

interface WordDetailProps {
  segment: NounSegment;
  mode: Mode;
  /** 語義の一覧(概念版で、見出し語のある語のとき)。 */
  senses: SensePickerState | null;
  /** 選び直した語義(変換し直している間も、選んだ語義を選んだ状態にする)。無ければ結果の語義。 */
  overriddenSynsetId: string | undefined;
  /** 変換中。操作を受け付けない(フォーカスは失わせない)。 */
  isBusy: boolean;
  /** 面を開いたときにフォーカスを移す見出し。 */
  headingRef: Ref<HTMLHeadingElement>;
  onToggleExclusion: () => void;
  onSelectSense: (synsetId: string) => void;
  onRetrySenses: () => void;
  onClose: () => void;
}

/**
 * 選んだ語の面([P1] F6〜F8)。置換経路、置き換えない指定の切り替え、語義の選び直しを置く。
 * 結果の下に置く。Esc で閉じる(フォーカスは画面が元の語に戻す)。
 */
export function WordDetail({
  segment,
  mode,
  senses,
  overriddenSynsetId,
  isBusy,
  headingRef,
  onToggleExclusion,
  onSelectSense,
  onRetrySenses,
  onClose,
}: WordDetailProps) {
  const sectionRef = useRef<HTMLElement>(null);
  // 面の中で Esc を押したら閉じる(面の中のどの部品にフォーカスがあっても)
  useEffect(() => {
    const section = sectionRef.current;
    if (section === null) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    section.addEventListener('keydown', handleKeyDown);
    return () => {
      section.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);
  const isExcluded = segment.status === 'excluded';
  const isReplaced = segment.status === 'replaced' || segment.status === 'climbed';
  return (
    <section className={styles.detail} aria-labelledby="word-detail-heading" ref={sectionRef}>
      <div className={styles.header}>
        <h2 id="word-detail-heading" className={styles.heading} ref={headingRef} tabIndex={-1}>
          選んだ語: {isReplaced ? `${segment.original} → ${segment.replaced}` : segment.original}
        </h2>
        <button type="button" className={styles.close} onClick={onClose}>
          閉じる
        </button>
      </div>
      <p className={styles.description}>{statusDescriptionOf(segment)}</p>
      {isReplaced && segment.route !== undefined && segment.route !== null && (
        <RoutePanel route={segment.route} original={segment.original} replaced={segment.replaced} />
      )}
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.toggle}
          aria-disabled={isBusy}
          onClick={() => {
            if (!isBusy) {
              onToggleExclusion();
            }
          }}
        >
          {isExcluded ? '置き換える(指定を外す)' : 'この語は置き換えない'}
        </button>
      </div>
      {!isExcluded && senses !== null && (
        <SensePicker
          state={senses}
          selectedSynsetId={overriddenSynsetId ?? segment.synsetId ?? undefined}
          isBusy={isBusy}
          onSelect={onSelectSense}
          onRetry={onRetrySenses}
        />
      )}
      {!isExcluded &&
        mode === 'gojuon' &&
        segment.lemma !== undefined &&
        segment.lemma !== null && (
          <p className={styles.note}>語義の選び直しは、概念版で使えます。</p>
        )}
    </section>
  );
}
