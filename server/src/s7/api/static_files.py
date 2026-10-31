"""画面のビルド結果(web/dist)の配信。

/ と /about は index.html を返す(画面のルーティングに任せる)。/api/ で始まるパスは静的配信に
回さない。Cache-Control は SecurityHeaders が付ける。
"""

from pathlib import Path
from typing import Final

from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

_INDEX_PATHS: Final = frozenset({"/", "/about"})
_API_PREFIX: Final = "/api/"
_NOT_FOUND: Final = 404


class SpaStaticFiles:
    """画面のファイルを返す。"""

    def __init__(self, directory: Path) -> None:
        """ビルド結果のディレクトリを受け取る。"""
        self._index = directory / "index.html"
        self._files = StaticFiles(directory=directory)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """パスに応じて index.html か、ビルド結果のファイルを返す。"""
        path: str = scope.get("path", "")
        if path.startswith(_API_PREFIX):
            # 存在しないAPIのパスは、FastAPIの既定と同じ形の404にする
            response = JSONResponse({"detail": "Not Found"}, status_code=_NOT_FOUND)
            await response(scope, receive, send)
            return
        if path in _INDEX_PATHS:
            await FileResponse(self._index)(scope, receive, send)
            return
        await self._files(scope, receive, send)


def has_built_web(directory: Path) -> bool:
    """画面がビルド済みか(開発中は Vite の開発サーバーが画面を配信するため、無くてよい)。"""
    return (directory / "index.html").is_file()
