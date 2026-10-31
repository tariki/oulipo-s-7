"""テスト全体の共通フィクスチャ。"""

import logging
from collections.abc import Iterator

import pytest

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
