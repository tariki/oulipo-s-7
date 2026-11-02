import { useCallback, useEffect, useRef, useState } from 'react';

import {
  charsBucketOf,
  createPageViewId,
  toEventErrorCode,
  trackEvent,
} from '../analytics/trackEvent';
import type { NounSegment, TransformResponse } from '../api/types';
import { CopyButton } from '../components/CopyButton';
import { Legend } from '../components/Legend';
import { ModeSelector } from '../components/ModeSelector';
import { NInput, isValidN } from '../components/NInput';
import { Panel } from '../components/Panel';
import { ResultView } from '../components/ResultView';
import { SiteHeader } from '../components/SiteHeader';
import { SkipLink } from '../components/SkipLink';
import { StatusBanner } from '../components/StatusBanner';
import { TextInput } from '../components/TextInput';
import type { SensePickerState } from '../components/SensePicker';
import { TransformButton } from '../components/TransformButton';
import { WordDetail } from '../components/WordDetail';
import { useApiClient } from '../hooks/apiClientContext';
import { type SensesState, useSenses } from '../hooks/useSenses';
import { type SettledTransform, type TransformState, useTransform } from '../hooks/useTransform';
import { joinReplaced } from '../segments/joinSegments';
import { countChars } from '../text/countChars';
import { errorMessage, sensesErrorMessage } from './messages';
import styles from './TransformPage.module.css';

const MAX_CHARS = 50_000;
const N_MIN = 1;
const N_MAX = 99;
const RESULT_ID = 'result';

/** 変換画面。フックと部品をつなぎ、解析のイベントを送る。 */
export function TransformPage() {
  const client = useApiClient();
  const [pageViewId] = useState(createPageViewId);
  const transformSeq = useRef(0);
  const [shownSeq, setShownSeq] = useState(0);

  useEffect(() => {
    trackEvent(client, { event: 'page_view', pageViewId });
  }, [client, pageViewId]);

  // [P1] 選んだ語(nounIndex。同じ入力文・同じ辞書の版なら同じ名詞を指す)。変換し直しても選んだままにする
  const [selection, setSelection] = useState<Selection | null>(null);

  const handleSettled = useCallback(
    (settled: SettledTransform) => {
      transformSeq.current += 1;
      const seq = transformSeq.current;
      const common = {
        event: 'transform' as const,
        pageViewId,
        transformSeq: seq,
        mode: settled.request.mode,
        n: settled.request.n,
        charsBucket: charsBucketOf(countChars(settled.request.text)),
      };
      if (settled.ok) {
        setShownSeq(seq);
        const { meta } = settled.response;
        trackEvent(client, {
          ...common,
          success: true,
          nounCount: meta.nounCount,
          excludedCount: meta.excludedCount,
          replacedCount: meta.replacedCount,
        });
      } else {
        // 結果が消えるため、選んだ語も忘れる(次の結果で面が急に開かないように)
        setSelection(null);
        trackEvent(client, {
          ...common,
          success: false,
          errorCode: toEventErrorCode(settled.error.code),
        });
      }
    },
    [client, pageViewId],
  );

  const transform = useTransform(client, handleSettled);
  const { state, text, mode, n } = transform;

  const chars = countChars(text);
  const isInputValid = text.trim() !== '' && chars <= MAX_CHARS && isValidN(n, N_MIN, N_MAX);
  const isLoading = state.status === 'loading';
  const isWaiting = transform.hasPendingRequest;

  // 変換し直している間と、文章を編集した後は、直前の結果を薄く残す
  const result = shownResultOf(state);
  const isStale = state.status !== 'success' && result !== undefined;

  const handleCopy = useCallback(() => {
    trackEvent(client, { event: 'copy', pageViewId, transformSeq: shownSeq });
  }, [client, pageViewId, shownSeq]);

  const detailHeading = useRef<HTMLHeadingElement>(null);
  const isFocusRequested = useRef(false);
  // 選べる結果(変換し直している間の直前の結果を含む。本文を編集した後の古い結果は除く)
  const isSelectable = state.status === 'success' || state.status === 'loading';
  const detailResult = isSelectable ? result : undefined;
  // 辞書の版が変わったら、選んだ語は使わない(nounIndex が別の名詞を指しうるため)
  const selectedIndex =
    selection !== null && detailResult?.meta.dictionaryVersion === selection.dictionaryVersion
      ? selection.nounIndex
      : null;
  const selected = selectedIndex === null ? undefined : nounSegmentAt(detailResult, selectedIndex);
  const sensesLemma =
    selected !== undefined &&
    detailResult?.meta.mode === 'concept' &&
    selected.status !== 'excluded' &&
    selected.lemma !== undefined &&
    selected.lemma !== null
      ? selected.lemma
      : undefined;
  const { state: senses, retry: retrySenses } = useSenses(
    sensesLemma,
    detailResult?.meta.dictionaryVersion ?? '',
  );

  const { setText: setTransformText } = transform;
  const handleTextChange = useCallback(
    (value: string) => {
      setSelection(null);
      setTransformText(value);
    },
    [setTransformText],
  );

  // 語を選んだら、面の見出しにフォーカスを移す(同じ語を選び直したときも)
  // 語を選ぶ関数の参照を変えない(段落を描き直さない)よう、表示中の辞書の版は ref から読む
  const shownVersion = useRef<string | undefined>(undefined);
  useEffect(() => {
    shownVersion.current = result?.meta.dictionaryVersion;
  }, [result]);
  const handleSelectToken = useCallback((nounIndex: number) => {
    const dictionaryVersion = shownVersion.current;
    if (dictionaryVersion === undefined) {
      return;
    }
    isFocusRequested.current = true;
    setSelection({ nounIndex, dictionaryVersion });
    detailHeading.current?.focus();
  }, []);
  useEffect(() => {
    if (isFocusRequested.current && selected !== undefined) {
      isFocusRequested.current = false;
      detailHeading.current?.focus();
    }
  }, [selected]);

  // 面を閉じたら、選んでいた語にフォーカスを戻す
  const handleCloseDetail = useCallback(() => {
    const index = selectedIndex;
    setSelection(null);
    if (index !== null) {
      document
        .querySelector<HTMLElement>(`#${RESULT_ID} [data-noun-index="${String(index)}"]`)
        ?.focus();
    }
  }, [selectedIndex]);

  const { toggleExclusion, overrideSense } = transform;
  const handleToggleExclusion = useCallback(() => {
    if (selectedIndex !== null) {
      toggleExclusion(selectedIndex);
    }
  }, [selectedIndex, toggleExclusion]);
  const handleSelectSense = useCallback(
    (synsetId: string) => {
      if (selectedIndex !== null) {
        overrideSense(selectedIndex, synsetId);
      }
    },
    [selectedIndex, overrideSense],
  );

  return (
    <div>
      <SkipLink targetId={RESULT_ID} />
      <SiteHeader isPageHeading />
      {/* 状態の変化を読み上げる領域。中身だけを差し替えるため、常に DOM に置く */}
      <p className={styles.visuallyHidden} aria-live="polite">
        {announcementOf(state, isWaiting, transform.isSlow)}
      </p>
      <main className={styles.main}>
        <Panel title="入力" tone="input">
          <TextInput value={text} maxChars={MAX_CHARS} onChange={handleTextChange} />
          <div className={styles.controls}>
            <ModeSelector value={mode} onChange={transform.setMode} />
            <NInput value={n} min={N_MIN} max={N_MAX} onChange={transform.setN} />
            <TransformButton
              isDisabled={!isInputValid}
              isBusy={isLoading}
              isWaiting={isWaiting}
              isSlow={transform.isSlow}
              onClick={transform.submit}
            />
          </div>
        </Panel>
        {(state.status === 'starting' || (state.status === 'checking' && isWaiting)) && (
          <StatusBanner
            tone="notice"
            message="準備中です。準備ができ次第、変換できるようになります"
          />
        )}
        {state.status === 'error' && (
          <StatusBanner tone="error" message={errorMessage(state.error)} />
        )}
        {state.status === 'idle' && isStale && (
          <StatusBanner
            tone="notice"
            message="文章が変わりました。変換し直すと結果が更新されます"
          />
        )}
        <Legend />
        {result !== undefined && (
          <ResultView
            id={RESULT_ID}
            result={result}
            isStale={isStale}
            isSelectable={isSelectable}
            actions={
              isStale ? undefined : (
                <CopyButton text={joinReplaced(result.segments)} onCopy={handleCopy} />
              )
            }
            onSelectToken={handleSelectToken}
          />
        )}
        {selected !== undefined && detailResult !== undefined && (
          <WordDetail
            segment={selected}
            mode={detailResult.meta.mode}
            senses={toPickerState(senses)}
            overriddenSynsetId={transform.senseOverrides[String(selected.nounIndex)]}
            isBusy={isLoading}
            headingRef={detailHeading}
            onToggleExclusion={handleToggleExclusion}
            onSelectSense={handleSelectSense}
            onRetrySenses={retrySenses}
            onClose={handleCloseDetail}
          />
        )}
      </main>
    </div>
  );
}

/** 選んだ語。辞書の版も覚える(版が変わると nounIndex が別の名詞を指しうるため)。 */
interface Selection {
  nounIndex: number;
  dictionaryVersion: string;
}

/** 結果の中の nounIndex の名詞。 */
function nounSegmentAt(result: TransformResponse | undefined, nounIndex: number) {
  return result?.segments.find(
    (segment): segment is NounSegment => segment.type === 'noun' && segment.nounIndex === nounIndex,
  );
}

/** 語義の一覧の取得の状態を、表示に要る形にする(取らない語は null)。 */
function toPickerState(senses: SensesState): SensePickerState | null {
  switch (senses.status) {
    case 'idle':
      return null;
    case 'error':
      return { status: 'error', message: sensesErrorMessage(senses.error) };
    default:
      return senses;
  }
}

/** 表示する結果(成功、変換し直している間の直前の結果、文章を編集した後の古い結果)。 */
function shownResultOf(state: TransformState) {
  switch (state.status) {
    case 'success':
      return state.result;
    case 'loading':
      return state.previousResult;
    case 'idle':
      return state.staleResult;
    default:
      return undefined;
  }
}

/** 読み上げ用の領域に出す文言(エラーは StatusBanner の alert が読み上げる)。 */
function announcementOf(state: TransformState, isWaiting: boolean, isSlow: boolean): string {
  if (state.status === 'starting' || (state.status === 'checking' && isWaiting)) {
    return '準備中です。準備ができ次第、変換できるようになります';
  }
  if (state.status === 'loading') {
    return isSlow ? '変換中です' : '';
  }
  if (state.status === 'success') {
    const { nounCount, replacedCount } = state.result.meta;
    return `変換しました。名詞${String(nounCount)}個のうち${String(replacedCount)}個を置き換えました`;
  }
  if (state.status === 'idle' && state.staleResult !== undefined) {
    return '文章が変わりました。変換し直すと結果が更新されます';
  }
  return '';
}
