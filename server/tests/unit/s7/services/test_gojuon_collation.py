import random
import unicodedata

import pytest

from s7.services.gojuon_collation import compute_sort_key

# 機能設計書「比較の例」の表のすべての行(小さい方, 大きい方)
COMPARISON_EXAMPLES = [
    ("あ", "ああ"),  # 第1キー(短い方が先)
    ("ああ", "あー"),  # 第3キー(母音 < 長音)
    ("あー", "あい"),  # 第1キー(ああ < あい)
    ("かつこう", "がっこう"),  # 第2キー
    ("しよう", "しょう"),  # 第3キー
    ("はは", "ばば"),  # 第2キー
    ("ばば", "ぱぱ"),  # 第2キー
    ("はば", "ばは"),  # 第2キー(先頭の文字から比べる)
    ("ん", "んー"),  # 第1キー(短い方が先)
    ("んん", "んー"),  # 第1キー(ん < ー)
    ("わ", "ゎ"),  # 第3キー
]


@pytest.mark.parametrize(("smaller", "larger"), COMPARISON_EXAMPLES)
def test_sort_key_orders_by_collation_rule(smaller: str, larger: str) -> None:
    assert compute_sort_key(smaller) < compute_sort_key(larger)


@pytest.mark.parametrize(
    ("reading", "keys"),
    [
        ("か", ("か", "0", "0")),  # 清音
        ("が", ("か", "1", "0")),  # 濁音
        ("ゔ", ("う", "1", "0")),
        ("ぱ", ("は", "2", "0")),  # 半濁音
        ("ゃ", ("や", "0", "1")),  # 小書き文字
        ("ゎ", ("わ", "0", "1")),
        ("ゕ", ("か", "0", "1")),
        ("ゖ", ("け", "0", "1")),
        ("ゐ", ("い", "0", "0")),
        ("ゑ", ("え", "0", "0")),
        ("ー", ("ー", "0", "2")),  # 先頭の長音は母音が無い
        ("かー", ("かあ", "00", "02")),  # 直前の母音
        ("ちゃー", ("ちやあ", "000", "012")),  # 小書き文字の後は置き換えた後の母音
        ("っー", ("つう", "00", "12")),  # 促音の後
        ("あーー", ("あああ", "000", "022")),  # 長音が続く
        ("んー", ("んー", "00", "02")),  # 「ん」の後は母音が無い
        ("んーー", ("んーー", "000", "022")),  # 母音の無い長音の後も母音が無い
        ("をー", ("をお", "00", "02")),
    ],
)
def test_sort_key_maps_each_char_to_three_keys(reading: str, keys: tuple[str, str, str]) -> None:
    assert compute_sort_key(reading) == "\u0000".join(keys)


def test_sort_key_rejects_char_outside_reading() -> None:
    # Given: カタカナは読みに使えない(呼び出し側でひらがなにしてから渡す)
    # When / Then
    with pytest.raises(ValueError, match=r"U\+30AB"):
        compute_sort_key("カ")


# --- 性質テスト: sort_key の大小と、照合規則を素直に実装した比較が一致する ---

_ALPHABET = [chr(c) for c in range(0x3041, 0x3097)] + ["ー"]
_SMALL_TO_LARGE = dict(zip("ぁぃぅぇぉっゃゅょゎゕゖ", "あいうえおつやゆよわかけ", strict=True))


def _vowel(char: str) -> str | None:
    """Unicodeの文字名の末尾の母音(例: HIRAGANA LETTER SMALL YA → あ)。"""
    name = unicodedata.name(char)
    last = name.split()[-1][-1]
    return {"A": "あ", "I": "い", "U": "う", "E": "え", "O": "お"}.get(last)


def _naive_levels(reading: str) -> tuple[list[str], list[int], list[int]]:
    """照合規則の3つの段階を、NFDの分解と文字名から素直に求める。"""
    primary: list[str] = []
    secondary: list[int] = []
    tertiary: list[int] = []
    for char in reading:
        if char == "ー":
            vowel = _vowel(primary[-1]) if primary and primary[-1] != "ー" else None
            primary.append(vowel or "ー")
            secondary.append(0)
            tertiary.append(2)
            continue
        decomposed = unicodedata.normalize("NFD", char)
        base, marks = decomposed[0], decomposed[1:]
        is_small = base in _SMALL_TO_LARGE
        base = _SMALL_TO_LARGE.get(base, base)
        base = {"ゐ": "い", "ゑ": "え"}.get(base, base)
        primary.append(base)
        secondary.append({"\u3099": 1, "\u309a": 2}.get(marks[0], 0) if marks else 0)
        tertiary.append(1 if is_small else 0)
    return primary, secondary, tertiary


def _naive_less(a: str, b: str) -> bool:
    return _naive_levels(a) < _naive_levels(b)


def _random_pairs(count: int) -> list[tuple[str, str]]:
    rng = random.Random(20261031)  # 決まった結果にするため固定する
    pairs = []
    for _ in range(count):
        a = "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 5)))
        # 半分は1文字だけ変えて、第2・第3キーまで比べる組にする
        if rng.random() < 0.5:
            i = rng.randrange(len(a))
            b = a[:i] + rng.choice(_ALPHABET) + a[i + 1 :]
        else:
            b = "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 5)))
        pairs.append((a, b))
    return pairs


@pytest.mark.parametrize(("a", "b"), _random_pairs(3000))
def test_sort_key_matches_naive_comparison(a: str, b: str) -> None:
    assert (compute_sort_key(a) < compute_sort_key(b)) == _naive_less(a, b)
