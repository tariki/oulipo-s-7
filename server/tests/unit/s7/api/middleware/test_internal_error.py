import pytest
from starlette.types import Message, Receive, Scope, Send

from s7.api.middleware.internal_error import InternalErrorMiddleware


async def _receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


@pytest.mark.anyio
async def test_error_after_response_started_is_reraised() -> None:
    """応答を送り始めた後の例外は、二重に応答しないよう、500を返さずに投げ直す。"""

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    with pytest.raises(RuntimeError):
        await InternalErrorMiddleware(app)({"type": "http", "path": "/api/v1/meta"}, _receive, send)
    assert [m["status"] for m in sent] == [200]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
