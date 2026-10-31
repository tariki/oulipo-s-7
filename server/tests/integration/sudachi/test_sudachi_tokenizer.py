import pytest

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.adapters.tokenizer import Tokenizer

pytestmark = pytest.mark.sudachi


@pytest.fixture(scope="module")
def tokenizer() -> SudachiTokenizer:
    return SudachiTokenizer()


def test_sudachi_tokenizer_satisfies_tokenizer_protocol(tokenizer: SudachiTokenizer) -> None:
    """Tokenizer として使える(型の検査は mypy、ここでは取り込みと呼び出しを確かめる)。"""
    protocol_typed: Tokenizer = tokenizer

    assert protocol_typed.tokenize("猫", "A")[0].surface == "猫"


def test_tokenize_mode_c_keeps_compound_as_one(tokenizer: SudachiTokenizer) -> None:
    """モードCは「図書館」を1語に保つ(見出し語の読みの決定で使う)。"""
    # When
    morphemes = tokenizer.tokenize("図書館司書", "C")

    # Then
    assert [(m.surface, m.reading_form) for m in morphemes] == [
        ("図書館", "トショカン"),
        ("司書", "シショ"),
    ]


def test_tokenize_mode_a_splits_into_smallest_units(tokenizer: SudachiTokenizer) -> None:
    """モードAは最も細かく区切る(機能設計書「1. 名詞抽出と最長一致」の例)。"""
    # When
    morphemes = tokenizer.tokenize("図書館", "A")

    # Then
    assert [m.surface for m in morphemes] == ["図書", "館"]
    assert morphemes[1].pos[:2] == ("接尾辞", "名詞的")


def test_tokenize_returns_normalized_form_and_pos(tokenizer: SudachiTokenizer) -> None:
    # When
    [morpheme] = tokenizer.tokenize("子ども", "C")

    # Then
    assert morpheme.normalized_form == "子供"
    assert morpheme.pos == ("名詞", "普通名詞", "一般", "*", "*", "*")
    assert not morpheme.is_oov


def test_tokenize_marks_unknown_word_as_oov(tokenizer: SudachiTokenizer) -> None:
    """辞書に無いカタカナ語は未知語になる(architecture.md「設計前の検証結果」の例)。"""
    # When
    [morpheme] = tokenizer.tokenize("アイサ", "C")

    # Then
    assert morpheme.is_oov


@pytest.mark.parametrize("text", ["夫々", "TCP/IP", "file allocation table", "$"])
def test_tokenize_gives_placeholder_reading_to_unreadable_symbol(
    tokenizer: SudachiTokenizer, text: str
) -> None:
    """読めない記号・空白の読みは「キゴウ」になる(辞書ビルダーはこの読みを使わない)。"""
    morphemes = tokenizer.tokenize(text, "C")

    assert any(m.pos[0] in ("補助記号", "空白") and m.reading_form == "キゴウ" for m in morphemes)
