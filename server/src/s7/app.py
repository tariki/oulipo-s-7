"""FastAPIアプリの組み立て。

依存関係を組み立てる唯一の場所(docs/repository-structure.md「app.py」)。
起動: uvicorn --factory s7.app:create_app --no-access-log
"""

import os
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.api.dependencies import Services
from s7.api.error_handlers import register_error_handlers
from s7.api.middleware.internal_error import InternalErrorMiddleware
from s7.api.middleware.request_logging import RequestLoggingMiddleware
from s7.api.middleware.startup_gate import StartupGateMiddleware
from s7.api.openapi_description import DESCRIPTION
from s7.api.routers import health, meta, senses, transform
from s7.config import Settings, load_settings
from s7.logging_config import configure_logging, log_app, log_error
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.meta_service import MetaService
from s7.services.noun_extractor import NounExtractor
from s7.services.sense_selector import SenseSelector
from s7.services.sense_service import SenseService
from s7.services.transform_service import TransformService

ServicesLoader = Callable[[Settings], Services]
FailureHandler = Callable[[BaseException], None]


def create_app(
    settings: Settings | None = None,
    load_services: ServicesLoader | None = None,
    on_load_failure: FailureHandler | None = None,
) -> FastAPI:
    """設定からアプリを作る。

    Args:
        settings: 実行時の設定。省略すると環境変数から読む。
        load_services: 変換用辞書を読み込んでサービスを組み立てる関数(テストで差し替える)。
        on_load_failure: 読み込みに失敗したときの処理。既定はプロセスを終了する。

    Returns:
        ルーターとミドルウェアを登録したアプリ。
    """
    resolved = settings if settings is not None else load_settings(os.environ)
    configure_logging(resolved.log_format, resolved.log_level)
    ready = threading.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 待ち受けるポートは Uvicorn の --port が決めるため、ログには出さない
        log_app("起動しました")
        # 画面の配信と /healthz を止めないよう、辞書は待ち受けを始めてから別スレッドで読み込む
        threading.Thread(
            target=_load,
            args=(
                app,
                resolved,
                load_services or _load_services,
                on_load_failure or _terminate,
                ready,
            ),
            name="dictionary-loader",
            daemon=True,
        ).start()
        yield
        log_app("終了しました")

    app = FastAPI(
        title="S+7メーカー API",
        description=DESCRIPTION,
        version="1",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.ready = ready
    register_error_handlers(app)
    for router in (health.router, transform.router, senses.router, meta.router):
        app.include_router(router)
    # 後に足したものほど外側になる。機能設計書「ミドルウェアと処理の順番」の内側から順に足す
    app.add_middleware(InternalErrorMiddleware)
    app.add_middleware(StartupGateMiddleware, is_ready=ready.is_set)
    app.add_middleware(RequestLoggingMiddleware)
    return app


def _load(
    app: FastAPI,
    settings: Settings,
    load_services: ServicesLoader,
    on_failure: FailureHandler,
    ready: threading.Event,
) -> None:
    started = time.perf_counter()
    try:
        services = load_services(settings)
    except Exception as error:
        log_error("辞書の読み込みに失敗しました", error)
        on_failure(error)
        return
    app.state.services = services
    log_app(
        "辞書を読み込みました",
        dictionary_version=services.meta.meta().dictionary_version,
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    ready.set()


def _load_services(settings: Settings) -> Services:
    """本物の変換用辞書とSudachiを読み込み、サービスを組み立てる。"""
    repo = DictionaryRepository.load(settings.dictionary_path)
    version = repo.meta().dictionary_version
    selector = SenseSelector(repo)
    transform_service = TransformService(
        NounExtractor(SudachiTokenizer(), repo),
        GojuonShifter(repo),
        ConceptShifter(repo, selector),
        version,
    )
    return Services(
        transform=transform_service, senses=SenseService(repo), meta=MetaService(version)
    )


def _terminate(_: BaseException) -> None:
    """読み込みに失敗したら、プロセスを終えてホスティング先に再起動させる。

    読み込みは別スレッドのため例外を投げても止まらない。ログを出した後に終了コード1で終える。
    """
    os._exit(1)
