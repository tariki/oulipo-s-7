import dataclasses

import pytest
from fixtures.lexicon import make_lexicon

from s7.domain.dictionary import Lemma, Sense, SiblingGroup, Synset
from s7.domain.errors import DictionaryIntegrityError
from s7.domain.transform import ConceptRef, ConceptStep
from s7.repositories.dictionary_repository import DictionaryData, DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.sense_selector import SenseSelector

# small_repo の兄弟グループ(wnjpn_sample.sql の木):
#   2: 上位語 90000010 → [12 犬, 13 キツネ, 11 ネコ, 15 未登録語]
#   1: 上位語 90000003 → [41 犬, 30 東京, 40 猫]
#   3: 上位語 90000011 → [20 三毛猫](兄弟が自分だけ)
# 見出し語: 0 犬、1 キツネ、3 東京、5 ネコ、6 猫、7 三毛猫、9 ル・コルビュジエ、10 未登録語


def _shifter(repo: DictionaryRepository) -> ConceptShifter:
    return ConceptShifter(repo, SenseSelector(repo))


def test_shift_moves_within_sibling_group(small_repo: DictionaryRepository) -> None:
    # When: 猫(語義 90000011)から1個先
    result = _shifter(small_repo).shift(6, 1)

    # Then
    assert result.sense.synset_id == "90000011-n"
    assert result.shift is not None
    assert result.shift.to_lemma.surface == "未登録語"  # 読みの無い語も置換後の語になる
    route = result.shift.route
    assert route.climbs == ()
    assert route.parent == ConceptRef("90000010-n", None, None)  # 見出し語の無い上位語
    assert route.from_ == ConceptRef("90000011-n", "ネコ", "ネコ科の動物；家で飼われる")
    assert route.to.synset_id == "90000015-n"
    assert (route.group_size, route.wrapped) == (4, False)


def test_shift_wraps_within_group(small_repo: DictionaryRepository) -> None:
    result = _shifter(small_repo).shift(6, 2)

    assert result.shift is not None
    assert result.shift.to_lemma.surface == "犬"
    assert result.shift.route.wrapped


def test_shift_full_cycle_returns_to_same_concept(small_repo: DictionaryRepository) -> None:
    """n % size == 0 なら元の概念に戻る(代表語が元の語と違う表記でもそのまま返す)。"""
    result = _shifter(small_repo).shift(6, 4)

    assert result.shift is not None
    assert result.shift.route.to.synset_id == "90000011-n"
    assert result.shift.to_lemma.surface == "ネコ"
    assert result.shift.route.wrapped


def test_shift_climbs_when_only_sibling(small_repo: DictionaryRepository) -> None:
    # When: 三毛猫は兄弟が自分だけ → 上位語の 90000011 の兄弟グループで進む
    result = _shifter(small_repo).shift(7, 1)

    # Then
    assert result.shift is not None
    route = result.shift.route
    assert [(s.from_.synset_id, s.to.synset_id, s.relation) for s in route.climbs] == [
        ("90000020-n", "90000011-n", "hypernym")
    ]
    assert route.from_.synset_id == "90000011-n"
    assert result.shift.to_lemma.surface == "未登録語"


def test_shift_without_sibling_up_to_top_returns_none(small_repo: DictionaryRepository) -> None:
    # ル・コルビュジエ: 自分だけ → 90000031(見出し語なし、兄弟グループなし) → 90000001(最上位)
    result = _shifter(small_repo).shift(9, 7)

    assert result.sense.synset_id == "90000032-n"
    assert result.shift is None


def test_shift_lemma_without_reading(small_repo: DictionaryRepository) -> None:
    """読みの無い見出し語も、語義と概念が分かれば置き換えられる。"""
    result = _shifter(small_repo).shift(10, 1)

    assert result.shift is not None
    assert result.shift.to_lemma.surface == "犬"


def test_shift_uses_sense_override(small_repo: DictionaryRepository) -> None:
    # 猫の2つ目の語義 90000040(グループ1の3番目)から1個先 → 先頭の 90000041(犬)
    result = _shifter(small_repo).shift(6, 1, synset_override="90000040-n")

    assert result.sense.is_override_applied
    assert result.shift is not None
    assert result.shift.route.to.synset_id == "90000041-n"


def _instance_tree() -> DictionaryRepository:
    """インスタンスの上位語で上がってから置き換わる木。

    90000001 都市(代表語 都市) ← [inst] 90000002 京都(兄弟は自分だけ)
    90000001 と 90000003 町 が、90000009 の兄弟グループ
    """
    lexicon = make_lexicon(["京都", "町", "都市"])  # id: 0 京都、1 町、2 都市
    synsets = (
        Synset("90000001-n", "90000009-n", "hypernym", 0, 1, 2, "都市の定義", None),
        Synset("90000002-n", "90000001-n", "instance_hypernym", 1, 0, 0, None, "Kyoto"),
        Synset("90000003-n", "90000009-n", "hypernym", 0, 0, 1, None, None),
        Synset("90000009-n", None, None, None, None, None, None, None),
    )
    groups = (
        SiblingGroup(0, "90000009-n", ("90000003-n", "90000001-n")),
        SiblingGroup(1, "90000001-n", ("90000002-n",)),
    )
    senses = (
        Sense(0, "90000002-n", 0, 0),
        Sense(1, "90000003-n", 0, 0),
        Sense(2, "90000001-n", 0, 0),
    )
    meta = dataclasses.replace(lexicon.meta(), synset_count=4)
    lemmas = tuple(lexicon.lemma(i) for i in range(3))
    return DictionaryRepository(DictionaryData(lemmas, synsets, groups, senses, meta))


def test_shift_climbs_instance_hypernym_and_uses_english_definition() -> None:
    result = _shifter(_instance_tree()).shift(0, 1)

    assert result.shift is not None
    assert result.shift.route.climbs == (
        ConceptStep(
            ConceptRef("90000002-n", "京都", "Kyoto"),  # 日本語の定義文が無ければ英語
            ConceptRef("90000001-n", "都市", "都市の定義"),
            "instance_hypernym",
        ),
    )
    assert result.shift.to_lemma == Lemma(1, "町", "あ", "あ\x000\x000")


def test_shift_with_missing_parent_is_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _instance_tree()
    original = repo.synset
    monkeypatch.setattr(repo, "synset", lambda i: None if i == "90000001-n" else original(i))

    with pytest.raises(DictionaryIntegrityError, match="概念 90000001-n"):
        _shifter(repo).shift(0, 1)
