"""本文が1MBを超えるリクエストを413(PAYLOAD_TOO_LARGE)で断る(BodySizeLimit)。

Content-Length があれば本文を読む前に判定する。無い場合(chunked)は読みながら数え、
上限を超えた時点で打ち切る。超えなければ、読んだ本文をそのまま内側へ渡し直す
(上限が1MBのため、メモリに持ってよい)。
"""

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from s7.api.error_handlers import error_response
from s7.domain import limits


class BodySizeLimitMiddleware:
    """本文の大きさを確かめる。"""

    def __init__(self, app: ASGIApp, max_bytes: int = limits.MAX_BODY_BYTES) -> None:
        """内側のアプリと上限(バイト数)を受け取る。"""
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """上限を超えていれば413を返し、超えていなければ内側へ渡す。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            is_too_large = content_length.isdigit() and int(content_length) > self.max_bytes
            if is_too_large:
                await self._reject(scope, receive, send)
                return
            # 宣言された長さを超える本文は、HTTPサーバー(Uvicorn)が受け付けない
            await self.app(scope, receive, send)
            return
        messages = await self._read_within_limit(receive)
        if messages is None:
            await self._reject(scope, receive, send)
            return
        await self.app(scope, _replay(messages, receive), send)

    async def _read_within_limit(self, receive: Receive) -> list[Message] | None:
        """本文を最後まで読む。上限を超えたらその時点でやめて None を返す。"""
        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                return messages
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                return None
            if not message.get("more_body", False):
                return messages

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        await error_response("PAYLOAD_TOO_LARGE", scope)(scope, receive, send)


def _replay(messages: list[Message], receive: Receive) -> Receive:
    """読んだ本文を先に返し、その後は元の receive(切断の通知など)に戻す。"""
    pending = list(messages)

    async def replay() -> Message:
        if pending:
            return pending.pop(0)
        return await receive()

    return replay
