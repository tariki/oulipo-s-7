import pytest

from s7.services.text_chunker import MAX_TOKENIZE_BYTES, split_for_tokenizer


def test_short_text_is_one_part() -> None:
    assert split_for_tokenizer("猫が好き。") == ["猫が好き。"]


def test_empty_text_has_no_part() -> None:
    assert split_for_tokenizer("") == []


@pytest.mark.parametrize(
    ("text", "max_bytes", "expected"),
    [
        # 改行の直後が最優先(句点が後ろにあっても改行で切る)
        ("あい\nうえ。おか", 21, ["あい\n", "うえ。おか"]),
        # 句点などの直後
        ("あい。うえ、おかき", 21, ["あい。", "うえ、おかき"]),
        ("ab!cdefgh", 5, ["ab!", "cdefg", "h"]),
        # 空白(全角空白を含む)の直後
        ("あい\u3000うえおか", 20, ["あい\u3000", "うえおか"]),
        # 文字の種類が変わる位置(ひらがな → 漢字)
        ("ねこ猫猫猫", 12, ["ねこ", "猫猫猫"]),
        # どれも無ければコードポイントの境界
        ("ねこねこねこ", 12, ["ねこねこ", "ねこ"]),
    ],
)
def test_split_prefers_higher_priority_cut(text: str, max_bytes: int, expected: list[str]) -> None:
    assert split_for_tokenizer(text, max_bytes) == expected


def test_split_does_not_cut_before_combining_char() -> None:
    # Given: か + 結合用の濁点(U+3099)。3文字目の直前では切れない
    text = "かか\u3099か"

    # When: 2文字分(6バイト)までしか入らない
    parts = split_for_tokenizer(text, 6)

    # Then
    assert parts == ["か", "か\u3099", "か"]


@pytest.mark.parametrize("joiner", ["\u200d", "\ufe0f", "\U000e0100"])
def test_split_does_not_cut_before_joiner_or_selector(joiner: str) -> None:
    text = f"aa{joiner}a"

    parts = split_for_tokenizer(text, 5)

    assert all(not part.startswith(joiner) for part in parts)
    assert "".join(parts) == text


def test_long_text_parts_fit_and_join_back() -> None:
    # Given: 改行も句点も無い、50,000文字(約150KB)のひらがなと漢字
    text = "ねこ猫" * 16_667

    # When
    parts = split_for_tokenizer(text)

    # Then
    assert "".join(parts) == text
    assert all(len(part.encode("utf-8")) <= MAX_TOKENIZE_BYTES for part in parts)
    assert len(parts) == 4


def test_char_wider_than_limit_is_its_own_part() -> None:
    """上限より大きい1文字でも止まらずに進む。"""
    assert split_for_tokenizer("🐈🐈", 3) == ["🐈", "🐈"]
