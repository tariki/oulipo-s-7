"""形態素解析の結果の型。"""

from dataclasses import dataclass
from typing import Literal

# Sudachiの分割モード。A: 最も細かい単位(名詞抽出)、C: 最も長い単位(見出し語の読みの決定)
SplitMode = Literal["A", "C"]


@dataclass(frozen=True, slots=True)
class Morpheme:
    """形態素。Tokenizer が返す。

    Attributes:
        surface: 表記。
        normalized_form: 正規化表記(例: 「子ども」→「子供」)。
        reading_form: 読み(カタカナ)。
        pos: 品詞(Sudachiの品詞体系の6要素)。
        is_oov: 未知語かどうか。
    """

    surface: str
    normalized_form: str
    reading_form: str
    pos: tuple[str, ...]
    is_oov: bool
