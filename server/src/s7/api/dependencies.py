"""ルーターに渡すサービスの取得(FastAPIの Depends)。

サービスは app.py が起動後に組み立てて app.state.services に入れる。読み込み中の呼び出しは
StartupGate が503で断るため、ここに来るときは必ず読み込み済み。
"""

from dataclasses import dataclass

from fastapi import Request

from s7.api.middleware.rate_limiter import RateLimiter
from s7.api.schemas.transform import TransformRequest
from s7.domain.errors import RateLimitedError
from s7.services.meta_service import MetaService
from s7.services.sense_service import SenseService
from s7.services.transform_service import TransformService


@dataclass(frozen=True, slots=True)
class Services:
    """ルーターが使うサービス。"""

    transform: TransformService
    senses: SenseService
    meta: MetaService


def get_services(request: Request) -> Services:
    """読み込み済みのサービスを返す。"""
    services: Services | None = getattr(request.app.state, "services", None)
    if services is None:
        # StartupGate を通っているため起きない。起きたら組み立ての誤り(500になる)
        raise RuntimeError("services are not loaded")
    return services


def transform_char_limit(body: TransformRequest, request: Request) -> None:
    """文字数の利用制限。入力検証の後に判定するため、ミドルウェアではなく依存関数にする。

    Raises:
        RateLimitedError: 直近60秒間の文字数の合計が上限を超えるとき(今回の分は加えない)。
    """
    limiter: RateLimiter = request.app.state.rate_limiter
    key: str | None = getattr(request.state, "rate_limit_key", None)
    if key is None:
        # 回数の利用制限(RateLimitMiddleware)を通っていない。対象のパスの設定の誤りで、
        # 文字数の制限が黙って無効にならないよう500にする
        raise RuntimeError("rate limit key is missing")
    retry_after = limiter.check_chars(key, len(body.text))
    if retry_after is not None:
        raise RateLimitedError(retry_after)
