"""接続元ごとの利用制限(RateLimiter)。

規則は docs/functional-design.md「RateLimiter」、接続元の取り方は docs/architecture.md「利用制限」。
回数はミドルウェア(RateLimitMiddleware)で、文字数は入力検証の後に変換のルーターの依存関数で判定する。
"""

import ipaddress
import math
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from s7.api.error_handlers import error_response
from s7.domain import limits
from s7.logging_config import log_app

Bucket = Literal["transform", "auxiliary"]

WINDOW_SECONDS: Final = 60.0
MAX_KEYS: Final = 10_000
_BUCKET_LIMITS: Final[Mapping[Bucket, int]] = {
    "transform": limits.TRANSFORM_REQUESTS_PER_MINUTE,
    "auxiliary": limits.AUXILIARY_REQUESTS_PER_MINUTE,
}
# パス → 回数の枠。プリフライト(OPTIONS)は数えない
_PATH_BUCKETS: Final[Mapping[str, Bucket]] = {
    "/api/v1/transform": "transform",
    "/api/v1/senses": "transform",
    "/api/v1/meta": "auxiliary",
    "/api/v1/events": "auxiliary",
}
_IPV6_PREFIX: Final = 64


@dataclass(slots=True)
class _Record:
    """1つの接続元の、窓の中の記録。"""

    counts: dict[Bucket, deque[float]] = field(
        default_factory=lambda: {bucket: deque() for bucket in _BUCKET_LIMITS}
    )
    chars: deque[tuple[float, int]] = field(default_factory=deque)

    def prune(self, oldest: float) -> None:
        for times in self.counts.values():
            while times and times[0] <= oldest:
                times.popleft()
        while self.chars and self.chars[0][0] <= oldest:
            self.chars.popleft()

    def is_empty(self) -> bool:
        return not self.chars and not any(self.counts.values())


class RateLimiter:
    """直近60秒間のスライディングウィンドウで、回数と文字数を数える。

    回数はイベントループから、文字数は同期の依存関数(スレッド)から呼ぶため、ロックで守る。
    接続元IPアドレスは窓の間だけメモリに持つ(ログには出さない)。
    """

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_KEYS,
        chars_per_minute: int = limits.CHARS_PER_MINUTE,
    ) -> None:
        """時刻の取り方(テストで差し替える)と、持つ接続元の数の上限を受け取る。"""
        self._clock = clock
        self._max_keys = max_keys
        self._chars_per_minute = chars_per_minute
        self._records: OrderedDict[str, _Record] = OrderedDict()
        self._lock = threading.Lock()
        self._last_sweep = clock()

    def check_count(self, key: str, bucket: Bucket) -> int | None:
        """回数の枠で受け付けるかを決め、受け付けたら数える。

        Returns:
            受け付けたらNone。断ったら Retry-After の秒数(最も古い記録が窓の外に出るまで)。
        """
        with self._lock:
            now = self._clock()
            times = self._record(key, now).counts[bucket]
            if len(times) >= _BUCKET_LIMITS[bucket]:
                return _seconds_until(times[0] + WINDOW_SECONDS, now)
            times.append(now)
            return None

    def check_chars(self, key: str, chars: int) -> int | None:
        """文字数の枠で受け付けるかを決め、受け付けたら加える。

        Returns:
            受け付けたらNone。断ったら Retry-After の秒数
            (今回の分が収まるまで古い記録が出ていく秒数)。
        """
        with self._lock:
            now = self._clock()
            record = self._record(key, now)
            total = sum(c for _, c in record.chars)
            if total + chars <= self._chars_per_minute:
                record.chars.append((now, chars))
                return None
            # 古い記録から順に窓の外に出たとして、今回の分が収まる時点を求める
            for recorded_at, recorded_chars in record.chars:
                total -= recorded_chars
                if total + chars <= self._chars_per_minute:
                    return _seconds_until(recorded_at + WINDOW_SECONDS, now)
            return _seconds_until(now + WINDOW_SECONDS, now)  # 1回の上限より大きい場合(起きない)

    def key_count(self) -> int:
        """記録を持っている接続元の数。"""
        with self._lock:
            return len(self._records)

    def _record(self, key: str, now: float) -> _Record:
        if now - self._last_sweep >= WINDOW_SECONDS:
            self._sweep(now)
        record = self._records.get(key)
        if record is None:
            if len(self._records) >= self._max_keys:
                self._records.popitem(last=False)  # 最も長く使われていない接続元を捨てる
            record = _Record()
            self._records[key] = record
        else:
            self._records.move_to_end(key)
        record.prune(now - WINDOW_SECONDS)
        return record

    def _sweep(self, now: float) -> None:
        """窓より古い記録を捨て、空になった接続元を消す(1分ごと)。"""
        self._last_sweep = now
        for key in list(self._records):
            record = self._records[key]
            record.prune(now - WINDOW_SECONDS)
            if record.is_empty():
                del self._records[key]


def _seconds_until(moment: float, now: float) -> int:
    return max(1, math.ceil(moment - now))


def client_key(scope: Scope, trusted_proxy_hops: int) -> str:
    """接続元のキー。IPv4はアドレス、IPv6は先頭64ビット。

    前段のプロキシが付ける X-Forwarded-For の、末尾から trusted_proxy_hops 番目を使う
    (先頭は偽装されうる)。無い・足りない・読めないときは直接の接続元を使い、WARNING を出す
    (IPアドレスはログに出さない)。
    """
    direct = scope["client"][0] if scope.get("client") else ""
    if trusted_proxy_hops == 0:
        return _normalize(direct) or direct
    # プロキシが値を別の行で足すこともあるため、すべての行を順につなげてから数える
    forwarded = ", ".join(Headers(scope=scope).getlist("x-forwarded-for"))
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    if len(hops) >= trusted_proxy_hops:
        key = _normalize(hops[-trusted_proxy_hops])
        if key is not None:
            return key
    _warn_forwarded_missing()
    return _normalize(direct) or direct


_warning_lock = threading.Lock()
_last_warning: list[float] = []


def _warn_forwarded_missing() -> None:
    """設定の誤りに気付くための WARNING。リクエストごとに出すと多すぎるため、1分に1回にする。"""
    now = time.monotonic()
    with _warning_lock:
        if _last_warning and now - _last_warning[0] < WINDOW_SECONDS:
            return
        _last_warning[:] = [now]
    log_app("接続元を X-Forwarded-For から取れませんでした", severity="WARNING")


def _normalize(address: str) -> str | None:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address):
        # デュアルスタックで待ち受けると、IPv4の接続元が ::ffff:a.b.c.d の形で来る。
        # /64 に丸めると全員が1つのキーにまとまるため、IPv4として扱う
        if ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/{_IPV6_PREFIX}", strict=False))
    return str(ip)


class RateLimitMiddleware:
    """回数の枠を超えたら429(RATE_LIMITED)を返す。"""

    def __init__(self, app: ASGIApp, limiter: RateLimiter, trusted_proxy_hops: int) -> None:
        """内側のアプリ、利用制限、信頼するプロキシの段数を受け取る。"""
        self.app = app
        self.limiter = limiter
        self.trusted_proxy_hops = trusted_proxy_hops

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """回数を数え、枠を超えていれば429を返す。接続元のキーを scope["state"] に残す。"""
        bucket = _PATH_BUCKETS.get(scope.get("path", "")) if scope["type"] == "http" else None
        if bucket is None or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        key = client_key(scope, self.trusted_proxy_hops)
        # 文字数の判定(変換のルーターの依存関数)で同じキーを使う
        scope.setdefault("state", {})["rate_limit_key"] = key
        retry_after = self.limiter.check_count(key, bucket)
        if retry_after is not None:
            response = error_response(
                "RATE_LIMITED",
                scope,
                details={"retryAfter": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
