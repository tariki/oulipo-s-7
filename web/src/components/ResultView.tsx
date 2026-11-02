import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef } from 'react';

import type { TransformResponse } from '../api/types';
import { splitParagraphs } from '../segments/splitParagraphs';
import { Panel } from './Panel';
import { ParagraphView } from './ParagraphView';
import styles from './ResultView.module.css';

interface ResultViewProps {
  id: string;
  result: TransformResponse;
  /** 直前の結果か(変換し直している間、文章を編集した後)。薄く表示する。 */
  isStale: boolean;
  /**
   * 語を選べるか(文章を編集した後の古い結果では選べなくする)。変換し直している間は選べるままにし、
   * 語を button から作り直さない(1万語を作り直さないため。選んだ語の面からフォーカスを戻せるように)。
   */
  isSelectable: boolean;
  /** 変換後の文章の見出しの横に置くもの(コピーのボタン)。 */
  actions?: React.ReactNode;
  /** [P1] 変換後の文章の語を選んだ。安定した参照を渡す(段落を描き直さないため)。 */
  onSelectToken?: (nounIndex: number) => void;
}

const TOKEN_SELECTOR = '[data-noun-token]';

/**
 * 結果ごとの通し番号(段落の key に使う)。新しい結果では、原文・変換後の段落を作り直す。
 * WebKit は content-visibility: auto の段落の中身を書き換えただけでは描き直さないことがあり、
 * 変換し直した結果が空に見えたため(Safari。E2E の desktop-webkit で確認)。
 * 結果のオブジェクトごとに番号を振るため、中身が同じでも新しく届いた結果なら作り直す
 * (結果の同一性を保つ最適化を入れると、作り直さなくなることに注意)。
 */
const generations = new WeakMap<TransformResponse, number>();
let nextGeneration = 0;
function generationOf(result: TransformResponse): number {
  let generation = generations.get(result);
  if (generation === undefined) {
    generation = nextGeneration;
    nextGeneration += 1;
    generations.set(result, generation);
  }
  return generation;
}

/**
 * 原文と変換後の文章を、それぞれ色の面に並べて表示する(PCは左右、スマートフォンは変換後が先)。
 * 変換後の語は、Tabキーでは1回で入り、中では左右の矢印キーで移る(ロービングタブインデックス)。
 */
export function ResultView({
  id,
  result,
  isStale,
  isSelectable,
  actions,
  onSelectToken,
}: ResultViewProps) {
  const paragraphs = useMemo(() => splitParagraphs(result.segments), [result]);
  const generation = generationOf(result);
  const replacedRef = useRef<HTMLDivElement>(null);
  // 最後にフォーカスがあった語。段落を作り直して語が消えたときに、同じ語へフォーカスを戻すため
  const lastFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const container = replacedRef.current;
    if (container === null) {
      return;
    }
    const handleFocusIn = (event: FocusEvent) => {
      if (event.target instanceof HTMLElement && event.target.matches(TOKEN_SELECTOR)) {
        lastFocused.current = event.target;
      }
    };
    // ほかの要素へ移ったら忘れる(語が消えて body に落ちたときは relatedTarget が無いため覚えたまま)
    const handleFocusOut = (event: FocusEvent) => {
      if (event.relatedTarget instanceof Node && !container.contains(event.relatedTarget)) {
        lastFocused.current = null;
      }
    };
    container.addEventListener('focusin', handleFocusIn);
    container.addEventListener('focusout', handleFocusOut);
    return () => {
      container.removeEventListener('focusin', handleFocusIn);
      container.removeEventListener('focusout', handleFocusOut);
    };
  }, []);

  // 最初の語だけを Tab で入れるようにする(1万語あっても Tab で結果を通り過ぎられるように)。
  // 結果を差し替えたときに Tab で入れる語が2つ以上にならないよう、全部を -1 に戻してから決める。
  // 段落を作り直してフォーカスのあった語が消えた(フォーカスが body に落ちた)ときは、新しい結果の
  // 同じ語へフォーカスを戻す。利用者がほかの所を押していたら(語は消えていない)戻さない
  useEffect(() => {
    const container = replacedRef.current;
    const tokens = Array.from(container?.querySelectorAll<HTMLElement>(TOKEN_SELECTOR) ?? []);
    const previous = lastFocused.current;
    const restored =
      previous !== null && !previous.isConnected && document.activeElement === document.body
        ? tokens.find((token) => token.dataset.nounIndex === previous.dataset.nounIndex)
        : undefined;
    const entry = restored ?? tokens[0];
    tokens.forEach((token) => {
      token.tabIndex = token === entry ? 0 : -1;
    });
    if (restored !== undefined) {
      restored.focus({ preventScroll: true });
    }
  }, [paragraphs, isSelectable]);

  // 段落を描き直さずに済むよう、tabIndex は DOM を直接切り替える
  const handleTokenKeyDown = useCallback((event: KeyboardEvent<HTMLButtonElement>) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    const container = replacedRef.current;
    if (step === undefined || container === null) {
      return;
    }
    const tokens = Array.from(container.querySelectorAll<HTMLElement>(TOKEN_SELECTOR));
    const next = tokens[tokens.indexOf(event.currentTarget) + step];
    if (next === undefined) {
      return;
    }
    event.preventDefault();
    event.currentTarget.tabIndex = -1;
    next.tabIndex = 0;
    next.focus();
  }, []);

  return (
    <section
      id={id}
      className={isStale ? styles.stale : styles.result}
      aria-label="変換の結果"
      tabIndex={-1}
    >
      <Panel title="変換後" tone="replaced" actions={actions} className={styles.replaced}>
        <div ref={replacedRef} className={styles.text}>
          {paragraphs.map((paragraph) => (
            <ParagraphView
              key={`${String(generation)}-${String(paragraph.index)}`}
              paragraph={paragraph}
              side="replaced"
              isSelectable={isSelectable}
              onTokenKeyDown={handleTokenKeyDown}
              onTokenSelect={onSelectToken}
            />
          ))}
        </div>
      </Panel>
      <Panel title="原文" tone="original" className={styles.original}>
        <div className={styles.text}>
          {paragraphs.map((paragraph) => (
            <ParagraphView
              key={`${String(generation)}-${String(paragraph.index)}`}
              paragraph={paragraph}
              side="original"
              isSelectable={false}
              onTokenKeyDown={handleTokenKeyDown}
            />
          ))}
        </div>
      </Panel>
    </section>
  );
}
