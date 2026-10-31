"""見出し語の読みを決める(ReadingAssigner)。

機能設計書「5. 見出し語の読みの決定」の実装。最初に決まった時点で終える。
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

from s7.adapters.tokenizer import Tokenizer

ReadingSource = Literal["kana", "sudachi"]

# 手順1: かなだけの表記(ひらがな・カタカナ・長音符・中黒)
_KANA_ONLY: Final = re.compile(r"[ぁ-ゖァ-ヺー・]+")
# 手順3: 読みに使ってよい文字(ぁ〜ゖ(ゔを含む)と長音)
_VALID_READING: Final = re.compile(r"[ぁ-ゖー]+")
_MIDDLE_DOT: Final = "・"
# Sudachiは読めない記号・空白(「々」「/」「$」、半角空白など)に仮の読み「キゴウ」を付ける
_PLACEHOLDER_READING: Final = "キゴウ"
_SYMBOL_POS: Final = frozenset({"補助記号", "空白"})
# カタカナ(ァ〜ヶ)をひらがな(ぁ〜ゖ)にする。ヴ→ゔ、ヵ→ゕ、ヶ→ゖ を含む
_KATAKANA_TO_HIRAGANA: Final = {code: code - 0x60 for code in range(0x30A1, 0x30F7)}


@dataclass(frozen=True, slots=True)
class Reading:
    """決まった読み。

    Attributes:
        reading: 読み(ひらがなと長音)。
        source: 決め方。kana: かなだけの表記から、sudachi: Sudachiのモードの読みから。
    """

    reading: str
    source: ReadingSource


class ReadingAssigner:
    """見出し語の表記から読みを決める。"""

    def __init__(self, tokenizer: Tokenizer) -> None:
        """読みの決定に使う Tokenizer を受け取る。

        Args:
            tokenizer: 形態素解析(モードCで使う)。テストでは偽物に差し替える。
        """
        self._tokenizer = tokenizer

    def assign(self, surface: str) -> Reading | None:
        """読みを決める。

        Args:
            surface: 見出し語の表記。

        Returns:
            決まった読み。決まらなければNone(五十音順リストに入れず、概念版でだけ使う)。
        """
        if _KANA_ONLY.fullmatch(surface):
            return _checked(surface, "kana")
        morphemes = self._tokenizer.tokenize(surface, "C")
        if any(m.is_oov for m in morphemes):
            return None
        if any(
            m.pos[0] in _SYMBOL_POS and m.reading_form == _PLACEHOLDER_READING for m in morphemes
        ):
            return None
        return _checked("".join(m.reading_form for m in morphemes), "sudachi")


def _checked(raw: str, source: ReadingSource) -> Reading | None:
    """中黒を除いてひらがなにし、読みに使えない文字や空なら None にする(手順3・4)。

    手順3の検査は、かなだけの表記から作った読みにも適用する(ヷ〜ヺ はひらがなに無いため)。
    """
    reading = raw.replace(_MIDDLE_DOT, "").translate(_KATAKANA_TO_HIRAGANA)
    if not _VALID_READING.fullmatch(reading):
        return None
    return Reading(reading=reading, source=source)
