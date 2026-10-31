import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';

import {
  charsBucketOf,
  createPageViewId,
  toEventErrorCode,
  trackEvent,
} from '../analytics/trackEvent';
import { CopyButton } from '../components/CopyButton';
import { Legend } from '../components/Legend';
import { ModeSelector } from '../components/ModeSelector';
import { NInput, isValidN } from '../components/NInput';
import { ResultView } from '../components/ResultView';
import { SkipLink } from '../components/SkipLink';
import { StatusBanner } from '../components/StatusBanner';
import { TextInput } from '../components/TextInput';
import { TransformButton } from '../components/TransformButton';
import { useApiClient } from '../hooks/apiClientContext';
import { type SettledTransform, type TransformState, useTransform } from '../hooks/useTransform';
import { joinReplaced } from '../segments/joinSegments';
import { countChars } from '../text/countChars';
import { errorMessage } from './messages';
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

  return (
    <div className={styles.page}>
      <SkipLink targetId={RESULT_ID} />
      <header className={styles.header}>
        <h1>S+7メーカー</h1>
        <nav aria-label="ページ">
          <Link to="/about">このアプリについて</Link>
          <a href="/api/docs">API</a>
        </nav>
      </header>
      {/* 状態の変化を読み上げる領域。中身だけを差し替えるため、常に DOM に置く */}
      <p className={styles.visuallyHidden} aria-live="polite">
        {announcementOf(state, isWaiting, transform.isSlow)}
      </p>
      <main className={styles.main}>
        <p className={styles.lead}>文章中の名詞を、辞書でN個先の語に置き換えます。</p>
        <TextInput value={text} maxChars={MAX_CHARS} onChange={transform.setText} />
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
            actions={
              isStale ? undefined : (
                <CopyButton text={joinReplaced(result.segments)} onCopy={handleCopy} />
              )
            }
          />
        )}
      </main>
    </div>
  );
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
