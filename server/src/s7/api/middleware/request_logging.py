"""/api/v1/* の呼び出しごとに kind = request のログを1行出す(RequestLogging)。

項目は docs/functional-design.md「ログの形式」。内側の段階が scope["state"] に残した
エラーコード(error_code)と、変換の mode・n・文字数(transform_log)を含める。
"""

import time
from typing import Final

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from s7.logging_config import log_request

_LOGGED_PREFIX: Final = "/api/v1/"
_INTERNAL_ERROR_STATUS: Final = 500


class RequestLoggingMiddleware:
    """APIの呼び出しを記録する。本文、クエリ文字列、IPアドレス、User-Agentは出さない。"""

    def __init__(self, app: ASGIApp) -> None:
        """内側のアプリを受け取る。"""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """内側を呼び、応答のステータスを見てから1行出す。"""
        if scope["type"] != "http" or not scope["path"].startswith(_LOGGED_PREFIX):
            await self.app(scope, receive, send)
            return
        state = scope.setdefault("state", {})
        started_at = time.perf_counter()
        status = _INTERNAL_ERROR_STATUS
        logged = False

        def log() -> None:
            nonlocal logged
            logged = True
            transform_log = state.get("transform_log") or {}
            log_request(
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - started_at) * 1000),
                client=Headers(scope=scope).get("x-s7-client"),
                error_code=state.get("error_code"),
                mode=transform_log.get("mode"),
                n=transform_log.get("n"),
                chars=transform_log.get("chars"),
            )

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            # 応答の最後の本文を送る前に出す(送った後だと、利用者が応答を受け取った後に
            # ログが出ることになり、ログの順番が応答の順番とずれうるため)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                log()
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if not logged:
                log()
