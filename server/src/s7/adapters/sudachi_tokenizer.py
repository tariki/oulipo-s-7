"""Sudachi(SudachiDict-core)による Tokenizer の実装。

取り込んでよいのは app.py と辞書ビルダーだけ(docs/repository-structure.md「依存関係のルール」)。
"""

from collections.abc import Mapping
from typing import Final

from sudachipy import Dictionary, SplitMode
from sudachipy import Tokenizer as SudachiCoreTokenizer

from s7.domain.text import Morpheme
from s7.domain.text import SplitMode as Mode

_SPLIT_MODES: Final[Mapping[Mode, SplitMode]] = {"A": SplitMode.A, "C": SplitMode.C}


class SudachiTokenizer:
    """Sudachiで文章を区切る。

    辞書は生成時に1回だけ読み込み、分割モードごとの Tokenizer を持つ。
    複数のスレッドから同時に使ってよいかは未確認のため、いまは1つのスレッドから使う
    (確かめる作業: docs/development-guidelines.md「パフォーマンス」)。
    """

    def __init__(self) -> None:
        """SudachiDict-core を読み込む。"""
        dictionary = Dictionary(dict="core")
        self._tokenizers: dict[Mode, SudachiCoreTokenizer] = {
            mode: dictionary.tokenizer(mode=split_mode) for mode, split_mode in _SPLIT_MODES.items()
        }

    def tokenize(self, text: str, mode: Mode) -> list[Morpheme]:
        """文章を区切る。

        Args:
            text: 区切る文章。UTF-8で40,000バイト以下。
            mode: 分割モード。

        Returns:
            形態素の列。
        """
        return [
            Morpheme(
                surface=m.surface(),
                normalized_form=m.normalized_form(),
                reading_form=m.reading_form(),
                pos=tuple(m.part_of_speech()),
                is_oov=m.is_oov(),
            )
            for m in self._tokenizers[mode].tokenize(text)
        ]
