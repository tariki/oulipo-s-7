import threading
import time
from collections.abc import Callable, Sequence

import pytest
from fixtures.fake_tokenizer import FakeTokenizer, morpheme

from s7.domain.text import Morpheme
from s7.domain.transform import Mode, NounResult, RawSegment, TransformResult
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.noun_extractor import NounExtractor
from s7.services.sense_selector import SenseSelector
from s7.services.transform_service import TransformService

# 名詞は先頭から 0 猫、1 犬、2 未知(辞書に無い)、3 ル・コルビュジエ、
# 4 未登録語(読みが無い)、5 三毛猫
SENTENCE: list[Morpheme] = [
    morpheme("猫"),
    morpheme("と", "particle"),
    morpheme("犬"),
    morpheme("と", "particle"),
    morpheme("未知"),
    morpheme("、", "symbol"),
    morpheme("ル・コルビュジエ"),
    morpheme("の", "particle"),
    morpheme("未登録語"),
    morpheme("と", "particle"),
    morpheme("三毛猫"),
    morpheme("。", "symbol"),
]
TEXT = "".join(m.surface for m in SENTENCE)


def _service(
    repo: DictionaryRepository, sentences: dict[str, Sequence[Morpheme]] | None = None
) -> TransformService:
    extractor = NounExtractor(FakeTokenizer(sentences=sentences or {TEXT: SENTENCE}), repo)
    selector = SenseSelector(repo)
    return TransformService(
        extractor,
        GojuonShifter(repo),
        ConceptShifter(repo, selector),
        repo.meta().dictionary_version,
    )


def _nouns(result: TransformResult) -> list[NounResult]:
    return [s for s in result.segments if isinstance(s, NounResult)]


def _summary(result: TransformResult) -> list[tuple[int, str, str, str | None]]:
    return [(r.noun_index, r.status, r.replaced, r.synset_id) for r in _nouns(result)]


def test_transform_gojuon(small_repo: DictionaryRepository) -> None:
    # When
    result = _service(small_repo).transform(TEXT, "gojuon", 1)

    # Then
    assert _summary(result) == [
        (0, "replaced", "三毛猫", None),
        (1, "replaced", "キツネ", None),
        (2, "not_in_dictionary", "未知", None),
        (3, "replaced", "犬", None),  # 末尾から先頭に戻る
        (4, "no_reading", "未登録語", None),
        (5, "replaced", "物", None),
    ]
    assert result.text == "三毛猫とキツネと未知、犬の未登録語と物。"
    assert [s for s in result.segments if isinstance(s, str)] == [
        "と",
        "と",
        "、",
        "の",
        "と",
        "。",
    ]
    assert _nouns(result)[3].route is not None
    assert _nouns(result)[2].lemma is None


def test_transform_concept(small_repo: DictionaryRepository) -> None:
    result = _service(small_repo).transform(TEXT, "concept", 1)

    assert _summary(result) == [
        (0, "replaced", "未登録語", "90000011-n"),
        (1, "replaced", "東京", "90000041-n"),
        (2, "not_in_dictionary", "未知", None),
        (3, "no_sibling", "ル・コルビュジエ", "90000032-n"),
        (4, "replaced", "犬", "90000015-n"),  # 読みの無い語も概念版では置き換える
        (5, "climbed", "未登録語", "90000020-n"),
    ]
    assert result.meta.replaced_count == 4  # replaced と climbed


def test_original_segments_join_back_to_input(small_repo: DictionaryRepository) -> None:
    modes: list[Mode] = ["gojuon", "concept"]
    for mode in modes:
        result = _service(small_repo).transform(TEXT, mode, 7)
        originals = "".join(s if isinstance(s, str) else s.original for s in result.segments)
        assert originals == TEXT


def test_transform_meta(small_repo: DictionaryRepository) -> None:
    result = _service(small_repo).transform(TEXT, "gojuon", 3)

    meta = result.meta
    assert (meta.mode, meta.n, meta.noun_count, meta.excluded_count, meta.replaced_count) == (
        "gojuon",
        3,
        6,
        0,
        4,
    )
    assert meta.dictionary_version == small_repo.meta().dictionary_version
    assert (meta.ignored_exclusions, meta.ignored_sense_overrides) == ((), ())


def test_exclusions_keep_original_and_report_unused(small_repo: DictionaryRepository) -> None:
    # When: 0 は使う。6・99 は名詞の数以上、-1 は範囲外
    result = _service(small_repo).transform(
        TEXT, "concept", 1, exclusions=frozenset({0, 6, 99, -1})
    )

    # Then
    excluded = _nouns(result)[0]
    assert (excluded.status, excluded.replaced, excluded.route) == ("excluded", "猫", None)
    assert excluded.lemma is not None  # 除外しても見出し語と語義は入れる
    assert excluded.synset_id == "90000011-n"
    assert result.meta.excluded_count == 1
    assert result.meta.ignored_exclusions == (-1, 6, 99)


def test_exclusion_has_priority_over_not_in_dictionary(small_repo: DictionaryRepository) -> None:
    result = _service(small_repo).transform(TEXT, "gojuon", 1, exclusions=frozenset({2}))

    assert _nouns(result)[2].status == "excluded"


def test_excluded_noun_in_gojuon_has_no_synset(small_repo: DictionaryRepository) -> None:
    result = _service(small_repo).transform(TEXT, "gojuon", 1, exclusions=frozenset({0}))

    assert (_nouns(result)[0].status, _nouns(result)[0].synset_id) == ("excluded", None)


def test_sense_overrides_in_concept_mode(small_repo: DictionaryRepository) -> None:
    # Given
    overrides = {
        0: "90000040-n",  # 猫の語義 → 使う
        1: "90000011-n",  # 犬の語義ではない → 使わない
        2: "90000011-n",  # 辞書に無い語 → 使わない
        3: "90000011-n",  # 除外した名詞 → 除外が優先。使わなかったことにもしない
        50: "90000011-n",  # 名詞の数以上 → 使わない
    }

    # When
    result = _service(small_repo).transform(
        TEXT, "concept", 1, exclusions=frozenset({3}), sense_overrides=overrides
    )

    # Then
    assert _nouns(result)[0].synset_id == "90000040-n"
    assert _nouns(result)[0].replaced == "犬"  # 90000040 の1個先は 90000041(犬)
    assert _nouns(result)[1].synset_id == "90000041-n"
    assert result.meta.ignored_sense_overrides == (1, 2, 50)


def test_excluded_noun_shows_overridden_sense(small_repo: DictionaryRepository) -> None:
    result = _service(small_repo).transform(
        TEXT, "concept", 1, exclusions=frozenset({0}), sense_overrides={0: "90000040-n"}
    )

    assert (_nouns(result)[0].status, _nouns(result)[0].synset_id) == ("excluded", "90000040-n")


def test_sense_overrides_are_not_used_or_reported_in_gojuon(
    small_repo: DictionaryRepository,
) -> None:
    """五十音順では語義の指定を使わない。画面がモードを切り替えても指定を保てるよう、無視したことにもしない。"""
    result = _service(small_repo).transform(
        TEXT, "gojuon", 1, sense_overrides={0: "90000040-n", 2: "x", 50: "x"}
    )

    assert _nouns(result)[0].replaced == "三毛猫"
    assert result.meta.ignored_sense_overrides == ()


@pytest.mark.parametrize("mode", ["gojuon", "concept"])
def test_text_without_nouns(small_repo: DictionaryRepository, mode: Mode) -> None:
    sentence = [morpheme("走る", "verb"), morpheme("。", "symbol")]

    result = _service(small_repo, {"走る。": sentence}).transform("走る。", mode, 7)

    assert result.segments == ("走る。",)
    assert result.meta.noun_count == 0


def test_text_starting_and_ending_with_noun_has_no_empty_string(
    small_repo: DictionaryRepository,
) -> None:
    sentence = [morpheme("猫"), morpheme("犬")]

    result = _service(small_repo, {"猫犬": sentence}).transform("猫犬", "gojuon", 1)

    assert all(isinstance(s, NounResult) for s in result.segments)
    assert len(result.segments) == 2


class _BlockingExtractor(NounExtractor):
    """呼ばれたら release されるまで止まり、同時に動いている数を数える。"""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.release = threading.Event()
        self._lock = threading.Lock()

    def extract(self, text: str) -> list[RawSegment]:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        self.release.wait(timeout=5)
        with self._lock:
            self.active -= 1
        return [text]


def _wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 5
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.01)


def test_transform_runs_at_most_two_at_once(small_repo: DictionaryRepository) -> None:
    # Given
    extractor = _BlockingExtractor()
    selector = SenseSelector(small_repo)
    service = TransformService(
        extractor, GojuonShifter(small_repo), ConceptShifter(small_repo, selector), "test"
    )

    # When: 5つを同時に呼び、2つが止まったところで少し待つ
    threads = [
        threading.Thread(target=service.transform, args=("文", "gojuon", 7)) for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    _wait_until(lambda: extractor.active == 2)
    time.sleep(0.1)  # 3つ目が入ってこないことを確かめる時間
    active_while_blocked = extractor.active
    extractor.release.set()
    for thread in threads:
        thread.join()

    # Then
    assert active_while_blocked == 2
    assert extractor.max_active == 2


@pytest.mark.parametrize("max_concurrency", [0, -1])
def test_max_concurrency_must_be_positive(
    small_repo: DictionaryRepository, max_concurrency: int
) -> None:
    selector = SenseSelector(small_repo)

    with pytest.raises(ValueError, match="max_concurrency"):
        TransformService(
            NounExtractor(FakeTokenizer(), small_repo),
            GojuonShifter(small_repo),
            ConceptShifter(small_repo, selector),
            "test",
            max_concurrency=max_concurrency,
        )
