"""テスト全体の共通フィクスチャ。"""

import logging
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fixtures.fake_tokenizer import FakeTokenizer
from fixtures.sample_wordnet import SAMPLE_EXCLUDED, SAMPLE_READINGS, create_sample_wordnet

from s7.app import create_app
from s7.config import REPO_ROOT, load_settings
from s7.repositories.dictionary_repository import DictionaryRepository
from s7builder.dictionary_builder import DictionaryBuilder

_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")

#: 本物の変換用辞書(スナップショットと性能のテストで使う。scripts/build-dictionary.sh で作る)
REAL_DICTIONARY = REPO_ROOT / "data" / "build" / "s7dict.sqlite"

#: 本物の辞書の読み込みを待つ上限(秒)
_READY_TIMEOUT_SECONDS = 120


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="スナップショットテストの期待値を書き直す(tests/snapshot/expected/)",
    )


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """configure_logging がルートとUvicornのロガーを書き換えるため、テストごとに元へ戻す。"""
    root = logging.getLogger()
    saved_root = (list(root.handlers), root.level)
    saved = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
            logging.getLogger(name).disabled,
        )
        for name in _LOGGER_NAMES
    }
    yield
    saved_handlers, saved_level = saved_root
    root.handlers = saved_handlers
    root.setLevel(saved_level)
    for name, (handlers, propagate, disabled) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.propagate = propagate
        logger.disabled = disabled


@pytest.fixture(scope="session")
def small_dictionary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """wnjpn_sample.sql から辞書ビルダーで作った小さな変換用辞書のファイル(セッションで1回)。"""
    directory = tmp_path_factory.mktemp("small_dictionary")
    excluded = directory / "excluded-lemmas.txt"
    excluded.write_text(SAMPLE_EXCLUDED, encoding="utf-8")
    output = directory / "s7dict.sqlite"
    builder = DictionaryBuilder(FakeTokenizer(SAMPLE_READINGS), "core-test", "license")
    builder.build(create_sample_wordnet(directory / "wnjpn.db"), excluded, output)
    return output


@pytest.fixture(scope="session")
def small_repo(small_dictionary: Path) -> DictionaryRepository:
    """小さな変換用辞書を読み込んだもの。"""
    return DictionaryRepository.load(small_dictionary)


@pytest.fixture(scope="session")
def real_client() -> Iterator[TestClient]:
    """本物の変換用辞書とSudachiで動くアプリ(セッションで1回だけ読み込む)。

    辞書が無ければ失敗させる(気付かずに飛ばさないため。開発ガイドライン「pytestの設定」)。
    """
    if not REAL_DICTIONARY.is_file():
        pytest.fail(
            f"本物の変換用辞書がありません: {REAL_DICTIONARY}"
            "(scripts/fetch-wordnet.sh と scripts/build-dictionary.sh で作ってください)"
        )

    # 読み込みは別のスレッドで動くため、失敗を覚えておき、待っている間に見つけたらすぐ止める
    load_errors: list[BaseException] = []

    def fail_loading(error: BaseException) -> None:
        load_errors.append(error)

    settings = load_settings(
        {"S7_DICTIONARY_PATH": str(REAL_DICTIONARY), "S7_LOG_LEVEL": "WARNING"}
    )
    with TestClient(create_app(settings, on_load_failure=fail_loading)) as client:
        deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
        while client.get("/api/v1/meta").status_code != 200:
            if load_errors:
                pytest.fail(f"本物の変換用辞書を読み込めませんでした: {load_errors[0]!r}")
            if time.monotonic() > deadline:
                pytest.fail(f"{_READY_TIMEOUT_SECONDS}秒たっても辞書の読み込みが終わりません")
            time.sleep(0.2)
        yield client
