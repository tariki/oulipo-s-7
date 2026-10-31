"""五十音順の照合規則。

機能設計書「2. 五十音順の照合規則」の実装。辞書ビルダーが見出し語を並べるときに使う。
照合規則を変えたら、辞書のバージョンを上げる(docs/development-guidelines.md「変換用辞書を変えるときの手順」)。
"""

from collections.abc import Mapping
from typing import Final

# 区切り文字。どの文字より小さいため、短い読みが先に並ぶ(「あ」<「ああ」)
_SEPARATOR: Final = "\u0000"
# 母音の無い長音(先頭、「ん」の後など)の第1キー。どのひらがなより大きい(末尾扱い)
_LONG_VOWEL: Final = "ー"

# 清音の大きな文字(ゐ・ゑを除く)。コードポイント順が五十音順と一致する
_SEION: Final = (
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
)
_DAKUON: Final = dict(
    zip(
        "がぎぐげござじずぜぞだぢづでどばびぶべぼゔ",
        "かきくけこさしすせそたちつてとはひふへほう",
        strict=True,
    )
)
_HANDAKUON: Final = dict(zip("ぱぴぷぺぽ", "はひふへほ", strict=True))
_SMALL: Final = dict(zip("ぁぃぅぇぉっゃゅょゎゕゖ", "あいうえおつやゆよわかけ", strict=True))
_OBSOLETE: Final = {"ゐ": "い", "ゑ": "え"}

# 読みの1文字 → (第1キー, 第2キー, 第3キー)。長音は直前の文字で決まるため別に扱う
_KEYS: Final[Mapping[str, tuple[str, str, str]]] = {
    **{c: (c, "0", "0") for c in _SEION},
    **{c: (base, "1", "0") for c, base in _DAKUON.items()},
    **{c: (base, "2", "0") for c, base in _HANDAKUON.items()},
    **{c: (base, "0", "1") for c, base in _SMALL.items()},
    **{c: (base, "0", "0") for c, base in _OBSOLETE.items()},
}

# 第1キーの文字 → 母音(段)。「ん」は母音を持たない
_VOWELS: Final[Mapping[str, str]] = {
    c: vowel
    for vowel, row in [
        ("あ", "あかさたなはまやらわ"),
        ("い", "いきしちにひみり"),
        ("う", "うくすつぬふむゆる"),
        ("え", "えけせてねへめれ"),
        ("お", "おこそとのほもよろを"),
    ]
    for c in row
}


def compute_sort_key(reading: str) -> str:
    """読みから並び替え用のキーを作る。

    3つのキー(第1: 清音にした文字、第2: 清音 < 濁音 < 半濁音、第3: 直音 < 小書き文字 < 長音)を
    区切り文字でつなぐ。キーの大小(Pythonの文字列の比較)が照合規則の順になる。

    Args:
        reading: 読み。ひらがな(ぁ〜ゖ、ゔ)と長音(ー)だけ。

    Returns:
        並び替え用のキー。

    Raises:
        ValueError: 読みに使えない文字があるとき。
    """
    primary: list[str] = []
    secondary: list[str] = []
    tertiary: list[str] = []
    for char in reading:
        if char == _LONG_VOWEL:
            # 直前の文字(置き換えた後の長音を含む)の母音にする。母音が無ければ末尾扱い
            previous = primary[-1] if primary else ""
            keys = (_VOWELS.get(previous, _LONG_VOWEL), "0", "2")
        elif char in _KEYS:
            keys = _KEYS[char]
        else:
            raise ValueError(f"読みに使えない文字です: U+{ord(char):04X}")
        primary.append(keys[0])
        secondary.append(keys[1])
        tertiary.append(keys[2])
    return _SEPARATOR.join(["".join(primary), "".join(secondary), "".join(tertiary)])
