"""セキュリティヘッダーと、パスごとの Cache-Control を付ける(SecurityHeaders)。

値は docs/architecture.md「HTTPヘッダー」。外側にあるため、内側の段階が返したどの応答にも付く。
"""

from typing import Final

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_COMMON: Final = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # HTTPで受けたブラウザは無視するため、手元でも害は無い
    "Strict-Transport-Security": "max-age=31536000",
}
# 画面だけに付ける。API仕様書(/api/docs)は外部のスクリプトを読み込むため付けない
_CONTENT_SECURITY_POLICY: Final = "default-src 'self'"
_NO_STORE: Final = "no-store"
_IMMUTABLE: Final = "public, max-age=31536000, immutable"
_NO_CACHE: Final = "no-cache"


def cache_control_for(path: str) -> str | None:
    """パスに付ける Cache-Control。API仕様書には付けない(None)。"""
    if path.startswith("/api/v1/") or path == "/healthz":
        return _NO_STORE
    if path.startswith("/api/"):
        return None
    # ファイル名にハッシュが付いた画面のファイル(Viteのビルド結果)
    if path.startswith("/assets/"):
        return _IMMUTABLE
    return _NO_CACHE


def _is_screen(path: str) -> bool:
    """画面(静的ファイル)のパスか。APIと起動確認には CSP を付けない。"""
    return not path.startswith("/api/") and path != "/healthz"


class SecurityHeadersMiddleware:
    """すべての応答にセキュリティヘッダーを付ける。"""

    def __init__(self, app: ASGIApp) -> None:
        """内側のアプリを受け取る。"""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """応答の開始のメッセージにヘッダーを足す。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _COMMON.items():
                    headers[name] = value
                if _is_screen(path):
                    headers["Content-Security-Policy"] = _CONTENT_SECURITY_POLICY
                cache_control = cache_control_for(path)
                if cache_control is not None:
                    headers["Cache-Control"] = cache_control
            await send(message)

        await self.app(scope, receive, send_wrapper)
