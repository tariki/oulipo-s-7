"""決まった形態素を返す Tokenizer。本物のSudachiの読みに左右されず、期待値を固定するため。"""

from collections.abc import Mapping

from s7.domain.text import Morpheme, SplitMode

_NOUN = ("名詞", "普通名詞", "一般", "*", "*", "*")


class FakeTokenizer:
    """表記と読みの対応表から形態素を返す。

    対応表にある文章は、その読みを持つ1つの形態素にする。読みのリストを渡すと、
    同じ数の形態素に分ける(表記は1つ目にまとめる)。対応表に無い文章は1つの未知語にする。
    """

    def __init__(self, readings: Mapping[str, str | list[str]]) -> None:
        self._readings = readings

    def tokenize(self, text: str, mode: SplitMode) -> list[Morpheme]:
        reading = self._readings.get(text)
        if reading is None:
            return [Morpheme(text, text, text, _NOUN, is_oov=True)]
        parts = [reading] if isinstance(reading, str) else reading
        surfaces = [text] + [""] * (len(parts) - 1)
        return [
            Morpheme(surface, surface, part, _NOUN, is_oov=False)
            for surface, part in zip(surfaces, parts, strict=True)
        ]
