"""Sudachi(SudachiDict-core)による Tokenizer の実装。

取り込んでよいのは app.py と辞書ビルダーだけ(docs/repository-structure.md「依存関係のルール」)。
"""

import threading
from collections.abc import Mapping
from typing import Final

from sudachipy import Dictionary, SplitMode
from sudachipy import Tokenizer as SudachiCoreTokenizer

from s7.domain.text import Morpheme
from s7.domain.text import SplitMode as Mode

_SPLIT_MODES: Final[Mapping[Mode, SplitMode]] = {"A": SplitMode.A, "C": SplitMode.C}


class SudachiTokenizer:
    """Sudachiで文章を区切る。複数のスレッドから同時に使ってよい。

    辞書は生成時に1回だけ読み込み、すべてのスレッドで共有する。SudachiPy の Tokenizer は
    同時に使うと SudachiError(Tokenizer is already in use)になるため、Tokenizer は
    スレッドごと・分割モードごとに作る(2026-10-31 に SudachiPy 0.7.0 で確認)。
    """

    def __init__(self) -> None:
        """SudachiDict-core を読み込む。"""
        self._dictionary = Dictionary(dict="core")
        self._local = threading.local()

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
            for m in self._tokenizer(mode).tokenize(text)
        ]

    def _tokenizer(self, mode: Mode) -> SudachiCoreTokenizer:
        """このスレッドの、分割モードの Tokenizer(初めて使うときに作る)。"""
        tokenizers: dict[Mode, SudachiCoreTokenizer] | None = getattr(
            self._local, "tokenizers", None
        )
        if tokenizers is None:
            tokenizers = {}
            self._local.tokenizers = tokenizers
        if mode not in tokenizers:
            tokenizers[mode] = self._dictionary.tokenizer(mode=_SPLIT_MODES[mode])
        return tokenizers[mode]
