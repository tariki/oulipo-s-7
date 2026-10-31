"""ルーターに渡すサービスの取得(FastAPIの Depends)。

サービスは app.py が起動後に組み立てて app.state.services に入れる。読み込み中の呼び出しは
StartupGate が503で断るため、ここに来るときは必ず読み込み済み。
"""

from dataclasses import dataclass

from fastapi import Request

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
