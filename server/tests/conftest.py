"""テスト全体の共通フィクスチャ。"""

import logging
from collections.abc import Iterator

import pytest
from fixtures.fake_tokenizer import FakeTokenizer
from fixtures.sample_wordnet import SAMPLE_EXCLUDED, SAMPLE_READINGS, create_sample_wordnet

from s7.repositories.dictionary_repository import DictionaryRepository
from s7builder.dictionary_builder import DictionaryBuilder

_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")


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
def small_repo(tmp_path_factory: pytest.TempPathFactory) -> DictionaryRepository:
    """wnjpn_sample.sql から辞書ビルダーで作った小さな変換用辞書(セッションで1回だけ作る)。"""
    directory = tmp_path_factory.mktemp("small_dictionary")
    excluded = directory / "excluded-lemmas.txt"
    excluded.write_text(SAMPLE_EXCLUDED, encoding="utf-8")
    output = directory / "s7dict.sqlite"
    builder = DictionaryBuilder(FakeTokenizer(SAMPLE_READINGS), "core-test", "license")
    builder.build(create_sample_wordnet(directory / "wnjpn.db"), excluded, output)
    return DictionaryRepository.load(output)
