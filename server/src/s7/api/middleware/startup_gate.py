"""辞書の読み込み中は503(SERVICE_STARTING)を返す(StartupGate)。

/api/v1/events は辞書を使わないため起動中も受け付ける。/healthz と画面の配信も止めない
(docs/architecture.md「コールドスタート対策」)。
"""

from collections.abc import Callable
from typing import Final

from starlette.types import ASGIApp, Receive, Scope, Send

from s7.api.error_handlers import error_response

_GATED_PREFIX: Final = "/api/v1/"
_ALWAYS_OPEN: Final = frozenset({"/api/v1/events"})


class StartupGateMiddleware:
    """読み込みが終わるまで、辞書を使うAPIを503で断る。"""

    def __init__(self, app: ASGIApp, is_ready: Callable[[], bool]) -> None:
        """内側のアプリと、読み込みが終わったかを返す関数を受け取る。"""
        self.app = app
        self.is_ready = is_ready

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """読み込み中で、辞書を使うAPIなら503を返す。"""
        path = scope.get("path", "")
        is_gated = path.startswith(_GATED_PREFIX) and path not in _ALWAYS_OPEN
        if scope["type"] == "http" and is_gated and not self.is_ready():
            response = error_response("SERVICE_STARTING", scope, headers={"Retry-After": "1"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
