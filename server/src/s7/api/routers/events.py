"""POST /api/v1/events(EventsRouter)。画面専用の匿名のアクセス解析。

辞書を使わないため、起動中も受け付ける。IPアドレスとUser-Agentは記録しない。
"""

from fastapi import APIRouter, Response

from s7.api.schemas.errors import ErrorResponse
from s7.api.schemas.events import AnalyticsEvent
from s7.logging_config import log_event

router = APIRouter()


@router.post(
    "/api/v1/events",
    status_code=204,
    response_class=Response,
    responses={400: {"model": ErrorResponse, "description": "イベントの項目の形式が違う"}},
    summary="画面専用の解析用。外部からの利用は想定しない",
)
async def post_event(event: AnalyticsEvent) -> Response:
    """イベントを構造化ログに1行出す(kind = analytics)。"""
    log_event(event.model_dump(by_alias=True, exclude_none=True))
    return Response(status_code=204)
