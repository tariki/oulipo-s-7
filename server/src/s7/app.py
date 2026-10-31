"""FastAPIアプリの組み立て。

依存関係を組み立てる唯一の場所(docs/repository-structure.md「app.py」)。
起動: uvicorn --factory s7.app:create_app --no-access-log
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from s7.api.routers import health
from s7.config import Settings, load_settings
from s7.logging_config import configure_logging, log_app


def create_app(settings: Settings | None = None) -> FastAPI:
    """設定からアプリを作る。

    Args:
        settings: 実行時の設定。省略すると環境変数から読む。

    Returns:
        ルーターを登録したアプリ。
    """
    resolved = settings if settings is not None else load_settings(os.environ)
    configure_logging(resolved.log_format, resolved.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # 待ち受けるポートは Uvicorn の --port が決めるため、ログには出さない
        log_app("起動しました")
        yield
        log_app("終了しました")

    app = FastAPI(
        title="S+7メーカー API",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    return app
