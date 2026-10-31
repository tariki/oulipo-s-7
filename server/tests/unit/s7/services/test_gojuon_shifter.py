import pytest

from s7.domain.transform import GojuonRoute
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.shifter import shift_index

# small_repo の五十音順リスト(10語): 0 犬、1 キツネ、2 実体、3 東京、4 動物、5 ネコ、6 猫、
# 7 三毛猫、8 物、9 ル・コルビュジエ。10 未登録語は読みが無い


@pytest.mark.parametrize(
    ("index", "n", "size", "expected"),
    [(0, 7, 10, (7, False)), (3, 7, 10, (0, True)), (8, 7, 10, (5, True)), (0, 99, 10, (9, True))],
)
def test_shift_index(index: int, n: int, size: int, expected: tuple[int, bool]) -> None:
    assert shift_index(index, n, size) == expected


def test_shift_moves_n_ahead_with_all_neighbors(small_repo: DictionaryRepository) -> None:
    # When: 犬から7個先(間の語は6個で、全部入る)
    result = GojuonShifter(small_repo).shift(0, 7)

    # Then
    assert result is not None
    assert result.to_lemma.surface == "三毛猫"
    assert result.route == GojuonRoute(
        from_index=0,
        to_index=7,
        wrapped=False,
        neighbors=("キツネ", "実体", "東京", "動物", "ネコ", "猫"),
        neighbors_omitted=0,
    )


def test_shift_omits_middle_neighbors_when_more_than_six(small_repo: DictionaryRepository) -> None:
    # When: 8個先(間の語は7個。最初と最後の3語だけ)
    result = GojuonShifter(small_repo).shift(0, 8)

    # Then
    assert result is not None
    assert result.route.neighbors == ("キツネ", "実体", "東京", "ネコ", "猫", "三毛猫")
    assert result.route.neighbors_omitted == 1


def test_shift_wraps_from_end_to_start(small_repo: DictionaryRepository) -> None:
    result = GojuonShifter(small_repo).shift(8, 7)  # 物

    assert result is not None
    assert result.to_lemma.surface == "ネコ"
    assert result.route.wrapped
    assert result.route.neighbors == ("ル・コルビュジエ", "犬", "キツネ", "実体", "東京", "動物")


@pytest.mark.parametrize(("n", "to"), [(1, "キツネ"), (99, "ル・コルビュジエ")])
def test_shift_n_limits(small_repo: DictionaryRepository, n: int, to: str) -> None:
    result = GojuonShifter(small_repo).shift(0, n)

    assert result is not None
    assert result.to_lemma.surface == to
    if n == 99:
        assert result.route.neighbors == ("キツネ", "実体", "東京", "猫", "三毛猫", "物")
        assert result.route.neighbors_omitted == 92
    else:
        assert result.route.neighbors == ()


def test_shift_lemma_without_reading_returns_none(small_repo: DictionaryRepository) -> None:
    """読みの無い見出し語は五十音順リストに無いため置き換えない(no_reading)。"""
    assert GojuonShifter(small_repo).shift(10, 7) is None
