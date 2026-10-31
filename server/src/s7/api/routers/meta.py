"""GET /api/v1/meta(MetaRouter)。"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from s7.api.dependencies import Services, get_services
from s7.api.schemas.meta import LimitsSchema, MetaResponse

router = APIRouter()


@router.get(
    "/api/v1/meta",
    response_model=MetaResponse,
    summary="辞書のバージョン、入力の上限、利用制限、出典",
)
async def get_meta(services: Annotated[Services, Depends(get_services)]) -> MetaResponse:
    """画面の準備中の確認にも使うため、変換が混んでいても詰まらないよう非同期関数にする。"""
    meta = services.meta.meta()
    return MetaResponse(
        dictionary_version=meta.dictionary_version,
        limits=LimitsSchema(**asdict(meta.limits)),
        attribution=meta.attribution,
    )
