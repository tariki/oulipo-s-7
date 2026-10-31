"""エラーレスポンスの形式(機能設計書「エラーレスポンスの形式」)。"""

from s7.api.schemas.base import CamelModel
from s7.domain.errors import ErrorCode


class ErrorBody(CamelModel):
    """エラーの中身。"""

    code: ErrorCode
    message: str
    details: dict[str, int] | None = None


class ErrorResponse(CamelModel):
    """エラーレスポンス。"""

    error: ErrorBody
