"""エラーを「エラーレスポンスの形式」にそろえる(ErrorHandler)。

エラーコードとHTTPステータス・メッセージの対応はここだけに書く
(docs/development-guidelines.md「入力検証とエラーコード」)。
"""

from collections.abc import Mapping, MutableMapping
from http import HTTPStatus
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from s7.api.schemas.errors import ErrorBody, ErrorResponse
from s7.domain import limits
from s7.domain.errors import DomainError, ErrorCode

ERROR_STATUS: Final[Mapping[ErrorCode, int]] = {
    "TEXT_EMPTY": 400,
    "TEXT_TOO_LONG": 400,
    "INVALID_MODE": 400,
    "INVALID_N": 400,
    "INVALID_REQUEST": 400,
    "LEMMA_NOT_FOUND": 404,
    "PAYLOAD_TOO_LARGE": 413,
    "RATE_LIMITED": 429,
    "SERVICE_STARTING": 503,
    "INTERNAL_ERROR": 500,
}

_MESSAGES: Final[Mapping[ErrorCode, str]] = {
    "TEXT_EMPTY": "文章を入力してください",
    "TEXT_TOO_LONG": "文章は{max_chars:,}文字以内で入力してください(現在: {actual_chars:,}文字)",
    "INVALID_MODE": "変換のルール(mode)は gojuon か concept で指定してください",
    "INVALID_N": f"N は{limits.N_MIN}〜{limits.N_MAX}の整数で指定してください",
    "INVALID_REQUEST": "リクエストの形式が正しくありません",
    "LEMMA_NOT_FOUND": "見出し語が辞書にありません",
    "PAYLOAD_TOO_LARGE": "リクエストの本文は1MB以内にしてください",
    "RATE_LIMITED": "混み合っています。{retry_after}秒後にもう一度お試しください",
    "SERVICE_STARTING": "準備中です。少し待ってからもう一度お試しください",
    "INTERNAL_ERROR": "変換に失敗しました。時間をおいてお試しください",
}

# 検証エラーの loc → エラーコード(載っていない loc は INVALID_REQUEST)
_FIELD_CODES: Final[Mapping[tuple[str | int, ...], ErrorCode]] = {
    ("body", "mode"): "INVALID_MODE",
    ("body", "n"): "INVALID_N",
}
_TEXT_LOC: Final = ("body", "text")


def error_response(
    code: ErrorCode,
    scope: MutableMapping[str, Any],
    details: Mapping[str, int] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """エラーレスポンスを作り、リクエストのログ用にコードを scope["state"] に残す。

    Args:
        code: エラーコード。
        scope: リクエストのASGIのscope。
        details: 補足の数値(文字数など)。メッセージの埋め込みにも使う。
        headers: 追加のヘッダー(Retry-After など)。

    Returns:
        エラーレスポンス。
    """
    scope.setdefault("state", {})["error_code"] = code
    message = _MESSAGES[code].format(**{_to_snake(k): v for k, v in (details or {}).items()})
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=dict(details) if details else None)
    )
    return JSONResponse(
        status_code=ERROR_STATUS[code],
        content=body.model_dump(by_alias=True, exclude_none=True),
        headers=dict(headers or {}),
    )


def register_error_handlers(app: FastAPI) -> None:
    """DomainError と入力検証エラーを、エラーレスポンスに変換する処理を登録する。"""
    app.add_exception_handler(DomainError, _handle_domain_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)  # type: ignore[arg-type]


async def _handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    retry_after = getattr(error, "retry_after", None)
    if retry_after is None:
        return error_response(error.code, request.scope)
    return error_response(
        error.code,
        request.scope,
        details={"retryAfter": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


async def _handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    # Pydanticのエラーの type と loc だけを使う。input・msg・ctx は本文が入りうるため使わない。
    # 例外は TEXT_TOO_LONG の文字数で、input の長さ(数値)だけを使う
    first = error.errors()[0]
    loc = tuple(first["loc"])
    kind = first["type"]
    if loc == _TEXT_LOC:
        if kind in ("text_empty", "missing"):
            return error_response("TEXT_EMPTY", request.scope)
        if kind == "string_too_long":
            details = {"maxChars": limits.MAX_CHARS, "actualChars": len(first["input"])}
            return error_response("TEXT_TOO_LONG", request.scope, details=details)
        return error_response("INVALID_REQUEST", request.scope)
    return error_response(_FIELD_CODES.get(loc, "INVALID_REQUEST"), request.scope)


async def _handle_http_error(request: Request, error: StarletteHTTPException) -> Response:
    # FastAPIは、本文をJSONとして読めない(文字コードが不正など)ときに、
    # 400 の HTTPException を投げる。これもエラーレスポンスの形式にそろえる。
    # 存在しないパスの404などは FastAPI の既定のまま返す
    if error.status_code == HTTPStatus.BAD_REQUEST:
        return error_response("INVALID_REQUEST", request.scope)
    return await http_exception_handler(request, error)


def _to_snake(name: str) -> str:
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in name)
