import { useCallback, useEffect, useReducer, useRef, useState } from 'react';

import type { ApiClient } from '../api/ApiClient';
import { ApiError } from '../api/ApiError';
import type { Mode, TransformRequest, TransformResponse } from '../api/types';
import { type Readiness, type ReadinessStatus, useServerReadiness } from './useServerReadiness';

/** 「変換中…」を出すまでの時間(二重送信の防止は即時)。 */
export const SLOW_THRESHOLD_MS = 1_000;

/** 変換画面の状態(用語集「変換画面の状態」、機能設計書「画面遷移図」)。 */
export type TransformState =
  | { status: 'checking' }
  | { status: 'starting' }
  | { status: 'idle'; staleResult?: TransformResponse }
  /** previousResult: 変換し直している間も薄く残す、直前の結果。 */
  | { status: 'loading'; previousResult?: TransformResponse }
  | { status: 'success'; result: TransformResponse }
  | { status: 'error'; error: ApiError };

/** 1回の変換の操作の結果(準備中の自動の再試行を含めて1回と数える)。解析のイベントに使う。 */
export type SettledTransform =
  | { request: TransformRequest; ok: true; response: TransformResponse }
  | { request: TransformRequest; ok: false; error: ApiError };

export interface UseTransformResult {
  text: string;
  mode: Mode;
  n: number;
  setText: (text: string) => void;
  setMode: (mode: Mode) => void;
  setN: (n: number) => void;
  state: TransformState;
  /** サーバーの準備の状態(準備中の表示に使う)。 */
  readiness: Readiness;
  /** 準備中に押された変換の操作を保持しているか。 */
  hasPendingRequest: boolean;
  /** 変換が1秒を超えたか(「変換中…」を出す)。 */
  isSlow: boolean;
  submit: () => void;
}

type Operation =
  | { phase: 'idle'; staleResult?: TransformResponse }
  | { phase: 'loading'; previousResult?: TransformResponse }
  | { phase: 'success'; result: TransformResponse }
  | { phase: 'error'; error: ApiError };

type Action =
  | { type: 'started'; previousResult?: TransformResponse }
  | { type: 'succeeded'; result: TransformResponse }
  | { type: 'failed'; error: ApiError }
  | { type: 'reset'; staleResult?: TransformResponse };

function withOptional<T extends object, K extends string, V>(
  base: T,
  key: K,
  value: V | undefined,
): T | (T & Record<K, V>) {
  return value === undefined ? base : { ...base, [key]: value };
}

function reduce(_: Operation, action: Action): Operation {
  switch (action.type) {
    case 'started':
      return withOptional({ phase: 'loading' as const }, 'previousResult', action.previousResult);
    case 'succeeded':
      return { phase: 'success', result: action.result };
    case 'failed':
      return { phase: 'error', error: action.error };
    case 'reset':
      return withOptional({ phase: 'idle' as const }, 'staleResult', action.staleResult);
  }
}

/** 表示している結果(成功、または薄く残している古い結果)。 */
function shownResult(operation: Operation): TransformResponse | undefined {
  switch (operation.phase) {
    case 'success':
      return operation.result;
    case 'idle':
      return operation.staleResult;
    case 'loading':
      return operation.previousResult;
    case 'error':
      return undefined;
  }
}

function isSameRequest(a: TransformRequest, b: TransformRequest): boolean {
  return a.text === b.text && a.mode === b.mode && a.n === b.n;
}

/**
 * 変換画面の状態と、変換の操作の順序(準備中の保持、503後の再試行、古い結果)を持つ。
 * サーバーの準備の確認(useServerReadiness)も内側で使う。表示は持たない。
 */
export function useTransform(
  client: ApiClient,
  onSettled?: (settled: SettledTransform) => void,
): UseTransformResult {
  const [text, setTextState] = useState('');
  const [mode, setModeState] = useState<Mode>('gojuon');
  const [n, setNState] = useState(7);
  const [operation, dispatch] = useReducer(reduce, { phase: 'idle' });
  // 保持した操作。描画用の state と、通知の中から読む ref の両方に持つ
  const [pending, setPendingState] = useState<TransformRequest | null>(null);
  const pendingRef = useRef<TransformRequest | null>(null);
  const [isSlow, setIsSlow] = useState(false);
  // 準備の確認の失敗・時間切れの後に文章を編集したら、エラーの表示を消す(失敗 → 入力待ち)。
  // 編集した時点の準備の状態を覚え、いまの状態と同じときだけ消す(失敗の前の編集では消さない)
  const [statusAtLastEdit, setStatusAtLastEdit] = useState<ReadinessStatus | null>(null);
  // 非同期の処理の中から最新の値を見るための参照
  const latestInput = useRef<TransformRequest>({ text, mode, n });
  const operationRef = useRef(operation);
  const runCounter = useRef(0);
  const isRunning = useRef(false);
  const settledCallback = useRef(onSettled);
  useEffect(() => {
    settledCallback.current = onSettled;
    operationRef.current = operation;
  }, [onSettled, operation]);

  const setPending = useCallback((request: TransformRequest | null) => {
    pendingRef.current = request;
    setPendingState(request);
  }, []);

  // run と準備の通知は互いを参照するため、run は ref を通して呼ぶ
  const runRef = useRef<(request: TransformRequest) => Promise<void>>(() => Promise.resolve());

  const handleReadinessChange = useCallback(
    (status: ReadinessStatus) => {
      const request = pendingRef.current;
      if (request === null) {
        return;
      }
      if (status === 'ready' || status === 'failed') {
        // 準備ができたら、保持した操作を実行する
        setPending(null);
        void runRef.current(request);
      } else if (status === 'timedOut') {
        // 20秒たっても準備ができなければ捨てる(この操作は失敗として1回数える)
        setPending(null);
        settledCallback.current?.({
          request,
          ok: false,
          error: new ApiError('SERVICE_STARTING'),
        });
      }
    },
    [setPending],
  );

  const readiness = useServerReadiness(client, handleReadinessChange);
  const { status: readinessStatus, markStarting } = readiness;
  const readinessStatusRef = useRef(readinessStatus);
  useEffect(() => {
    readinessStatusRef.current = readinessStatus;
  }, [readinessStatus]);

  const run = useCallback(
    async (request: TransformRequest) => {
      if (isRunning.current) {
        return;
      }
      isRunning.current = true;
      const previous = shownResult(operationRef.current);
      dispatch({ type: 'started', previousResult: previous });
      runCounter.current += 1;
      const id = runCounter.current;
      const slowTimer = setTimeout(() => {
        if (runCounter.current === id) {
          setIsSlow(true);
        }
      }, SLOW_THRESHOLD_MS);
      try {
        const result = await client.transform(request);
        if (latestInput.current.text === request.text) {
          dispatch({ type: 'succeeded', result });
        } else {
          // 変換中に文章が変わった: 結果は古いものとして薄く出す
          dispatch({ type: 'reset', staleResult: result });
        }
        settledCallback.current?.({ request, ok: true, response: result });
      } catch (caught) {
        const error = ApiError.from(caught);
        if (error.code !== 'SERVICE_STARTING') {
          dispatch({ type: 'failed', error });
          settledCallback.current?.({ request, ok: false, error });
        } else if (isSameRequest(request, latestInput.current)) {
          // 準備中に戻り、同じ操作を保持して、準備ができ次第やり直す
          markStarting(error.retryAfterSeconds);
          setPending(request);
          dispatch({ type: 'reset', staleResult: previous });
        } else {
          // 変換中に入力が変わっていたら、古い操作は保持しない(操作を捨てる)
          markStarting(error.retryAfterSeconds);
          dispatch({ type: 'reset', staleResult: previous });
        }
      } finally {
        clearTimeout(slowTimer);
        setIsSlow(false);
        isRunning.current = false;
      }
    },
    [client, markStarting, setPending],
  );
  useEffect(() => {
    runRef.current = run;
  }, [run]);

  const updateInput = useCallback(
    (change: Partial<TransformRequest>) => {
      latestInput.current = { ...latestInput.current, ...change };
      // 待っている間に入力を変えたら、保持した操作を捨てる
      setPending(null);
    },
    [setPending],
  );

  const setText = useCallback(
    (value: string) => {
      updateInput({ text: value });
      setTextState(value);
      setStatusAtLastEdit(readinessStatusRef.current);
      // 結果の表示中・失敗の後に文章を編集したら、入力待ちに戻す(結果は薄く残す)
      if (operation.phase === 'success') {
        dispatch({ type: 'reset', staleResult: operation.result });
      } else if (operation.phase === 'error') {
        dispatch({ type: 'reset' });
      }
    },
    [operation, updateInput],
  );

  const setMode = useCallback(
    (value: Mode) => {
      updateInput({ mode: value });
      setModeState(value);
    },
    [updateInput],
  );

  const setN = useCallback(
    (value: number) => {
      updateInput({ n: value });
      setNState(value);
    },
    [updateInput],
  );

  const submit = useCallback(() => {
    if (isRunning.current) {
      return; // 二重送信の防止
    }
    const request: TransformRequest = { text, mode, n };
    if (readinessStatus === 'checking' || readinessStatus === 'starting') {
      // 確認中・準備中は、その時点の入力の写しを1件だけ保持する
      setPending(request);
      return;
    }
    // 準備済み、確認の失敗、時間切れの後: そのまま送る(503なら準備中に戻る)
    void run(request);
  }, [text, mode, n, readinessStatus, run, setPending]);

  return {
    text,
    mode,
    n,
    setText,
    setMode,
    setN,
    state: toState(operation, readiness, statusAtLastEdit === readinessStatus),
    readiness,
    hasPendingRequest: pending !== null,
    isSlow: operation.phase === 'loading' && isSlow,
    submit,
  };
}

/** 変換の操作の状態と、サーバーの準備の状態から、画面の状態を決める。 */
function toState(
  operation: Operation,
  readiness: Readiness,
  isReadinessErrorDismissed: boolean,
): TransformState {
  switch (operation.phase) {
    case 'loading':
      return withOptional(
        { status: 'loading' as const },
        'previousResult',
        operation.previousResult,
      );
    case 'success':
      return { status: 'success', result: operation.result };
    case 'error':
      return { status: 'error', error: operation.error };
    case 'idle':
      break;
  }
  const idle = withOptional({ status: 'idle' as const }, 'staleResult', operation.staleResult);
  switch (readiness.status) {
    case 'checking':
      return { status: 'checking' };
    case 'starting':
      return { status: 'starting' };
    case 'timedOut':
      return isReadinessErrorDismissed
        ? idle
        : { status: 'error', error: new ApiError('SERVICE_STARTING') };
    case 'failed':
      return isReadinessErrorDismissed
        ? idle
        : { status: 'error', error: readiness.error ?? new ApiError('NETWORK_ERROR') };
    case 'ready':
      return idle;
  }
}
