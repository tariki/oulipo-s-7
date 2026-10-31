"""APIの統合テストの共通フィクスチャ。

本物の辞書とSudachiは使わず、小さな変換用辞書(small_repo)と、語の一覧で区切る偽物の
Tokenizer でサービスを組み立てる。読み込みのスレッドが終わるまで待ってから返す。
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fixtures.fake_tokenizer import WordListTokenizer

from s7.api.dependencies import Services
from s7.app import create_app
from s7.config import Settings, load_settings
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.meta_service import MetaService
from s7.services.noun_extractor import NounExtractor
from s7.services.sense_selector import SenseSelector
from s7.services.sense_service import SenseService
from s7.services.transform_service import TransformService

# small_repo の見出し語(と、辞書に無い名詞として「未知」)
WORDS = [
    "実体",
    "動物",
    "物",
    "猫",
    "ネコ",
    "犬",
    "キツネ",
    "未登録語",
    "三毛猫",
    "東京",
    "ル・コルビュジエ",
    "未知",
]


def build_services(repo: DictionaryRepository) -> Services:
    version = repo.meta().dictionary_version
    selector = SenseSelector(repo)
    return Services(
        transform=TransformService(
            NounExtractor(WordListTokenizer(WORDS), repo),
            GojuonShifter(repo),
            ConceptShifter(repo, selector),
            version,
        ),
        senses=SenseService(repo),
        meta=MetaService(version),
    )


def _fail_test(error: BaseException) -> None:
    raise AssertionError("辞書の読み込みに失敗しました") from error


@pytest.fixture
def make_app(small_repo: DictionaryRepository) -> Callable[..., FastAPI]:
    """テスト用のアプリを作る関数。既定では small_repo のサービスを読み込む。"""

    def make(
        settings: Settings | None = None,
        load_services: Callable[[Settings], Services] | None = None,
        on_load_failure: Callable[[BaseException], None] = _fail_test,
    ) -> FastAPI:
        return create_app(
            settings or load_settings({}),
            load_services=load_services or (lambda _: build_services(small_repo)),
            on_load_failure=on_load_failure,
        )

    return make


@pytest.fixture
def client(make_app: Callable[..., FastAPI]) -> Iterator[TestClient]:
    """読み込みが終わったアプリの TestClient。"""
    app = make_app()
    with TestClient(app) as test_client:
        assert app.state.ready.wait(timeout=5)
        yield test_client
