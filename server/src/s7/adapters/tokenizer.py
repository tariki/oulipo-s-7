"""形態素解析のインターフェース。テストでは偽物(tests/fixtures/fake_tokenizer.py)に差し替える。"""

from typing import Protocol

from s7.domain.text import Morpheme, SplitMode


class Tokenizer(Protocol):
    """文章を形態素に区切る。"""

    def tokenize(self, text: str, mode: SplitMode) -> list[Morpheme]:
        """文章を区切る。

        Args:
            text: 区切る文章。UTF-8で40,000バイト以下(機能設計書「7. 長文の分割」)。
            mode: 分割モード。

        Returns:
            形態素の列。表記をつなげると text に戻る。
        """
        ...
