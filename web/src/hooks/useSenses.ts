import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../api/ApiError';
import type { SenseItem } from '../api/types';
import { useApiClient } from './apiClientContext';

/** 語義の一覧の取得の状態([P1: F8])。 */
export type SensesState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; senses: readonly SenseItem[] }
  | { status: 'error'; error: ApiError };

export interface UseSensesResult {
  state: SensesState;
  /** 失敗したあと、同じ語の一覧を取り直す。 */
  retry: () => void;
}

interface Fetched {
  key: string;
  attempt: number;
  result: { ok: true; senses: readonly SenseItem[] } | { ok: false; error: ApiError };
}

/** 覚えておく鍵。辞書の版が変わったら語義も変わりうるため、版も含める。 */
function keyOf(lemma: string, dictionaryVersion: string): string {
  return `${dictionaryVersion}\n${lemma}`;
}

/**
 * 見出し語の語義の一覧を取る。取れた一覧は辞書の版と見出し語ごとに覚え、同じ語を選び直しても取り直さない。
 * 失敗は覚えない(retry か、語を選び直せば取り直す)。
 */
export function useSenses(lemma: string | undefined, dictionaryVersion: string): UseSensesResult {
  const client = useApiClient();
  const [cache, setCache] = useState<ReadonlyMap<string, readonly SenseItem[]>>(new Map());
  // 最後に届いた結果。エフェクトの中で同期的に状態を変えないよう、どの鍵の結果かを一緒に持つ
  const [latest, setLatest] = useState<Fetched | null>(null);
  // 取り直した回数(増やすとエフェクトが走り直す)
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);
  const key = lemma === undefined ? null : keyOf(lemma, dictionaryVersion);
  const cached = key === null ? undefined : cache.get(key);

  useEffect(() => {
    if (lemma === undefined || key === null || cached !== undefined) {
      return;
    }
    let isCurrent = true;
    client.getSenses(lemma).then(
      (response) => {
        setCache((previous) => new Map(previous).set(key, response.senses));
        if (isCurrent) {
          setLatest({ key, attempt, result: { ok: true, senses: response.senses } });
        }
      },
      (caught: unknown) => {
        if (isCurrent) {
          setLatest({ key, attempt, result: { ok: false, error: ApiError.from(caught) } });
        }
      },
    );
    return () => {
      isCurrent = false;
    };
  }, [client, lemma, key, cached, attempt]);

  return { state: stateOf(key, cached, latest, attempt), retry };
}

function stateOf(
  key: string | null,
  cached: readonly SenseItem[] | undefined,
  latest: Fetched | null,
  attempt: number,
): SensesState {
  if (key === null) {
    return { status: 'idle' };
  }
  if (cached !== undefined) {
    return { status: 'success', senses: cached };
  }
  // 取り直している間は、前の失敗を出さない
  if (latest?.key === key && latest.attempt === attempt && !latest.result.ok) {
    return { status: 'error', error: latest.result.error };
  }
  return { status: 'loading' };
}
