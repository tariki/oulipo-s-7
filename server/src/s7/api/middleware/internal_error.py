"""想定外の例外を500(INTERNAL_ERROR)の応答にする。

Starletteの ServerErrorMiddleware は最も外側にあり、そこで作った500にはCORSヘッダーも
リクエストのログも付かない。そのため、自前のミドルウェアの最も内側で捕まえる。
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from s7.api.error_handlers import error_response
from s7.logging_config import log_error


class InternalErrorMiddleware:
    """内側で起きた想定外の例外を500にし、例外のクラス名と場所だけを記録する。"""

    def __init__(self, app: ASGIApp) -> None:
        """内側のアプリを受け取る。"""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """リクエストを内側へ渡し、例外が出たら500を返す。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as error:
            # 例外のメッセージには入力値が入りうるため、log_error は型と場所だけを出す
            log_error("想定外のエラー", error)
            if started:
                raise
            await error_response("INTERNAL_ERROR", scope)(scope, receive, send)
