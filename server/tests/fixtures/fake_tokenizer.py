"""決まった形態素を返す Tokenizer。本物のSudachiに左右されず、期待値を固定するため。"""

from collections.abc import Mapping, Sequence
from typing import Final, Literal

from s7.domain.text import Morpheme, SplitMode

# 形態素の種類 → Sudachiの品詞(6要素)
MorphemeKind = Literal[
    "noun",
    "proper",
    "numeral",
    "prefix",
    "suffix",
    "pronoun",
    "particle",
    "verb",
    "symbol",
    "space",
]
_POS: Final[Mapping[MorphemeKind, tuple[str, ...]]] = {
    "noun": ("名詞", "普通名詞", "一般", "*", "*", "*"),
    "proper": ("名詞", "固有名詞", "地名", "一般", "*", "*"),
    "numeral": ("名詞", "数詞", "*", "*", "*", "*"),
    "prefix": ("接頭辞", "*", "*", "*", "*", "*"),
    "suffix": ("接尾辞", "名詞的", "一般", "*", "*", "*"),
    "pronoun": ("代名詞", "*", "*", "*", "*", "*"),
    "particle": ("助詞", "格助詞", "*", "*", "*", "*"),
    "verb": ("動詞", "一般", "*", "*", "五段-ラ行", "終止形-一般"),
    "symbol": ("補助記号", "句点", "*", "*", "*", "*"),
    "space": ("空白", "*", "*", "*", "*", "*"),
}


def morpheme(
    surface: str, kind: MorphemeKind = "noun", normalized_form: str | None = None
) -> Morpheme:
    """テスト用の形態素を作る。読みは表記と同じにする。"""
    return Morpheme(surface, normalized_form or surface, surface, _POS[kind], is_oov=False)


class FakeTokenizer:
    """対応表から形態素を返す。

    sentences に文章がそのままあれば、その形態素の列を返す(名詞抽出のテスト用)。
    readings にあれば、その読みを持つ形態素にする(読みの決定のテスト用)。読みのリストを渡すと、
    同じ数の形態素に分ける(表記は1つ目にまとめる)。どちらにも無い文章は1つの未知語にする。
    """

    def __init__(
        self,
        readings: Mapping[str, str | list[str]] | None = None,
        sentences: Mapping[str, Sequence[Morpheme]] | None = None,
    ) -> None:
        self._readings = readings or {}
        self._sentences = sentences or {}

    def tokenize(self, text: str, mode: SplitMode) -> list[Morpheme]:
        if text in self._sentences:
            return list(self._sentences[text])
        reading = self._readings.get(text)
        if reading is None:
            return [Morpheme(text, text, text, _POS["noun"], is_oov=True)]
        parts = [reading] if isinstance(reading, str) else reading
        surfaces = [text] + [""] * (len(parts) - 1)
        return [
            Morpheme(surface, surface, part, _POS["noun"], is_oov=False)
            for surface, part in zip(surfaces, parts, strict=True)
        ]


class WordListTokenizer:
    """決まった語の一覧で、どんな文章も区切る(APIの統合テスト用)。

    先頭から、一覧の語のうち最も長く一致するものを普通名詞の形態素にし、
    一致しなければ1文字を助詞の形態素にする。表記をつなげると元の文章に戻る。
    """

    def __init__(self, words: Sequence[str]) -> None:
        self._words = sorted(set(words), key=len, reverse=True)

    def tokenize(self, text: str, mode: SplitMode) -> list[Morpheme]:
        morphemes: list[Morpheme] = []
        position = 0
        while position < len(text):
            word = next((w for w in self._words if text.startswith(w, position)), None)
            if word is None:
                morphemes.append(morpheme(text[position], "particle"))
                position += 1
            else:
                morphemes.append(morpheme(word))
                position += len(word)
        return morphemes
