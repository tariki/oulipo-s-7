"""本物のSudachiの入力の上限(機能設計書「7. 長文の分割」)。SudachiPyを上げるときに必ず通す。"""

import threading

import pytest

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.services.text_chunker import MAX_TOKENIZE_BYTES, split_for_tokenizer

pytestmark = pytest.mark.sudachi

SUDACHI_MAX_BYTES = 49_149


@pytest.fixture(scope="module")
def tokenizer() -> SudachiTokenizer:
    return SudachiTokenizer()


def test_input_up_to_limit_is_accepted(tokenizer: SudachiTokenizer) -> None:
    assert tokenizer.tokenize("a" * SUDACHI_MAX_BYTES, "A")


def test_input_over_limit_fails(tokenizer: SudachiTokenizer) -> None:
    """上限が変わったら、MAX_TOKENIZE_BYTES(40,000)に余裕があるかを見直す。"""
    # SudachiError は型として公開されていないため、メッセージで確かめる
    with pytest.raises(Exception, match="too long"):
        tokenizer.tokenize("a" * (SUDACHI_MAX_BYTES + 1), "A")


def test_chunked_long_text_is_accepted(tokenizer: SudachiTokenizer) -> None:
    # Given: 50,000文字(約150KB)
    text = "吾輩は猫である。名前はまだ無い。" * 3125

    # When
    parts = split_for_tokenizer(text)

    # Then
    assert MAX_TOKENIZE_BYTES < SUDACHI_MAX_BYTES
    for part in parts:
        assert "".join(m.surface for m in tokenizer.tokenize(part, "A")) == part


def test_tokenizer_can_be_shared_between_threads(tokenizer: SudachiTokenizer) -> None:
    """1つの SudachiTokenizer を複数のスレッドから同時に使っても例外にならない。"""
    text = "吾輩は猫である。名前はまだ無い。" * 500
    errors: list[BaseException] = []

    def run() -> None:
        try:
            for _ in range(10):
                assert "".join(m.surface for m in tokenizer.tokenize(text, "A")) == text
        # スレッドの中の失敗(assert を含む)を集めて、本体で確かめる
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []


def test_each_thread_gets_its_own_tokenizer() -> None:
    """Sudachiの Tokenizer はスレッドごと・分割モードごとに作り、同じスレッドでは使い回す。"""
    tokenizer = SudachiTokenizer()
    created: list[object] = []

    def run() -> None:
        created.append(tokenizer._tokenizer("A"))
        assert tokenizer._tokenizer("A") is created[-1]

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
        thread.join()

    assert len(created) == 2
    assert created[0] is not created[1]
