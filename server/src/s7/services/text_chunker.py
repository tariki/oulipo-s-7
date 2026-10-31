"""長文をSudachiに渡せる長さに分ける。

機能設計書「7. 長文の分割」の実装。Sudachiは1回の入力がUTF-8で約49KBを超えると例外になる。
"""

import unicodedata
from collections.abc import Callable
from typing import Final

MAX_TOKENIZE_BYTES: Final = 40_000

_SENTENCE_ENDS: Final = frozenset("。．！？!?")
# この文字の直前では切らない(異体字セレクタ、ゼロ幅接合子。結合文字は一般カテゴリで判定する)
_ZERO_WIDTH_JOINER: Final = "\u200d"
_VARIATION_SELECTORS: Final = (range(0xFE00, 0xFE10), range(0xE0100, 0xE01F0))
# 文字の種類と、そのコードポイントの範囲(「文字の種類が変わる位置」で切るため)
_KIND_RANGES: Final = (
    ("hiragana", (range(0x3041, 0x30A0),)),
    ("katakana", (range(0x30A0, 0x3100), range(0x31F0, 0x3200), range(0xFF66, 0xFFA0))),
    (
        "kanji",
        (
            range(0x4E00, 0xA000),
            range(0x3400, 0x4DC0),
            range(0xF900, 0xFB00),
            range(0x20000, 0x40000),
        ),
    ),
)
_KANJI_MARKS: Final = frozenset("々〆〇")


def split_for_tokenizer(text: str, max_bytes: int = MAX_TOKENIZE_BYTES) -> list[str]:
    """文章を、UTF-8で max_bytes 以下の部分に分ける。

    収まる範囲で、できるだけ後ろの、優先順の高い位置で切る(改行の直後 → 句点などの直後 →
    空白の直後 → 文字の種類が変わる位置 → コードポイントの境界)。

    Args:
        text: 文章。単独のサロゲート(U+D800〜U+DFFF)を含まないこと(UTF-8にできないため。
            APIの入力検証で lone_surrogate として断る)。
        max_bytes: 1つの部分のUTF-8のバイト数の上限。

    Returns:
        分けた部分。順につなげると text に戻る。空の部分は作らない。
    """
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = _fitting_end(text, start, max_bytes)
        cut = end if end == len(text) else _choose_cut(text, start, end)
        parts.append(text[start:cut])
        start = cut
    return parts


def _fitting_end(text: str, start: int, max_bytes: int) -> int:
    """text[start:end] がUTF-8で max_bytes 以下になる最大の end。少なくとも1文字は含める。"""
    total = 0
    end = start
    while end < len(text):
        total += len(text[end].encode("utf-8"))
        if total > max_bytes:
            break
        end += 1
    return max(end, start + 1)


def _choose_cut(text: str, start: int, end: int) -> int:
    """(start, end] の中で、優先順の高い規則に合う最も後ろの位置を返す。

    どの規則でも、結合文字・異体字セレクタ・ゼロ幅接合子の直前では切らない。
    """
    rules: list[Callable[[int], bool]] = [
        lambda p: text[p - 1] == "\n",
        lambda p: text[p - 1] in _SENTENCE_ENDS,
        lambda p: text[p - 1].isspace(),
        lambda p: _char_kind(text[p - 1]) != _char_kind(text[p]),
        lambda p: True,
    ]
    for rule in rules:
        for position in range(end, start, -1):
            if _can_cut_before(text[position]) and rule(position):
                return position
    return end


def _can_cut_before(char: str) -> bool:
    code = ord(char)
    is_variation_selector = any(code in r for r in _VARIATION_SELECTORS)
    is_combining = unicodedata.category(char).startswith("M")
    return not (is_variation_selector or is_combining or char == _ZERO_WIDTH_JOINER)


def _char_kind(char: str) -> str:
    """文字の種類(漢字・ひらがな・カタカナ・英数字・その他)。"""
    code = ord(char)
    for kind, ranges in _KIND_RANGES:
        if any(code in r for r in ranges) or (kind == "kanji" and char in _KANJI_MARKS):
            return kind
    return "alnum" if char.isalnum() else "other"
