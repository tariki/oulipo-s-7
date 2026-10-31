import { useCallback, useEffect, useRef, useState } from 'react';

import type { ApiClient } from '../api/ApiClient';
import { ApiError } from '../api/ApiError';
import type { MetaResponse } from '../api/types';

/** 準備ができるのを待つ上限(機能設計書「コールドスタート時の画面」)。 */
export const READINESS_TIMEOUT_MS = 20_000;

export type ReadinessStatus = 'checking' | 'starting' | 'ready' | 'timedOut' | 'failed';

interface ReadinessState {
  status: ReadinessStatus;
  meta: MetaResponse | null;
  /** 確認に失敗したときのエラー(status が failed のとき)。 */
  error: ApiError | null;
}

export interface Readiness extends ReadinessState {
  /** 変換のリクエストが503になったときに呼ぶ。最初の503の時点から20秒を数え、再試行する。 */
  markStarting: (retryAfterSeconds: number | null) => void;
}

/**
 * GET /api/v1/meta で準備ができたかを確かめる。503(SERVICE_STARTING)の間は
 * Retry-After の秒数ごとに再試行し、期限(20秒)を過ぎたら諦める。React に依存しない。
 */
export class ReadinessPoller {
  private deadline = Date.now() + READINESS_TIMEOUT_MS;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private isStopped = false;

  constructor(
    private readonly client: ApiClient,
    private readonly update: (state: Partial<ReadinessState>) => void,
  ) {}

  /** 確認を始める。20秒は画面を開いた時点(この時点)から数える。 */
  start(): void {
    this.deadline = Date.now() + READINESS_TIMEOUT_MS;
    void this.check();
  }

  stop(): void {
    this.isStopped = true;
    this.clearTimer();
  }

  /** 変換が503になったら、その時点から20秒を数え直して再試行する。 */
  markStarting(retryAfterSeconds: number | null): void {
    if (this.isStopped) {
      return;
    }
    this.clearTimer();
    this.deadline = Date.now() + READINESS_TIMEOUT_MS;
    this.update({ status: 'starting' });
    this.scheduleRetry(retryAfterSeconds);
  }

  private async check(): Promise<void> {
    try {
      const meta = await this.client.getMeta();
      if (!this.isStopped) {
        this.update({ status: 'ready', meta, error: null });
      }
    } catch (caught) {
      if (this.isStopped) {
        return;
      }
      const error = ApiError.from(caught);
      if (error.code === 'SERVICE_STARTING') {
        this.update({ status: 'starting' });
        this.scheduleRetry(error.retryAfterSeconds);
      } else {
        this.update({ status: 'failed', error });
      }
    }
  }

  private scheduleRetry(retryAfterSeconds: number | null): void {
    const remaining = this.deadline - Date.now();
    if (remaining <= 0) {
      this.update({ status: 'timedOut' });
      return;
    }
    const delay = Math.min((retryAfterSeconds ?? 1) * 1000, remaining);
    this.timer = setTimeout(() => {
      this.timer = null;
      if (Date.now() >= this.deadline) {
        this.update({ status: 'timedOut' });
        return;
      }
      void this.check();
    }, delay);
  }

  private clearTimer(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}

/**
 * サーバーの準備ができたか(機能設計書「コールドスタート時の画面」)。
 * onStatusChange は状態が変わるたびに呼ぶ(保持した変換の操作を、準備ができ次第実行するため)。
 */
export function useServerReadiness(
  client: ApiClient,
  onStatusChange?: (status: ReadinessStatus) => void,
): Readiness {
  const [state, setState] = useState<ReadinessState>({
    status: 'checking',
    meta: null,
    error: null,
  });
  const poller = useRef<ReadinessPoller | null>(null);
  const statusListener = useRef(onStatusChange);
  useEffect(() => {
    statusListener.current = onStatusChange;
  }, [onStatusChange]);

  useEffect(() => {
    const instance = new ReadinessPoller(client, (update) => {
      setState((previous) => ({ ...previous, ...update }));
      if (update.status !== undefined) {
        statusListener.current?.(update.status);
      }
    });
    poller.current = instance;
    instance.start();
    return () => {
      instance.stop();
    };
  }, [client]);

  const markStarting = useCallback((retryAfterSeconds: number | null) => {
    poller.current?.markStarting(retryAfterSeconds);
  }, []);

  return { ...state, markStarting };
}
