import pytest
from fixtures.lexicon import make_lexicon

from s7.domain.errors import DictionaryIntegrityError
from s7.domain.transform import SenseChoice
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.sense_selector import SenseSelector


def test_select_uses_highest_score(small_repo: DictionaryRepository) -> None:
    # 犬: 90000041(頻度9)が 90000012(頻度2)より先
    assert SenseSelector(small_repo).select(0) == SenseChoice(
        "90000041-n", is_override_applied=False
    )


def test_select_breaks_tie_by_synset_id(small_repo: DictionaryRepository) -> None:
    # 猫: 90000011 と 90000040 は同点(5)。概念IDの小さい方
    assert SenseSelector(small_repo).select(6).synset_id == "90000011-n"


def test_select_uses_override_of_own_sense(small_repo: DictionaryRepository) -> None:
    choice = SenseSelector(small_repo).select(0, override="90000012-n")

    assert choice == SenseChoice("90000012-n", is_override_applied=True)


def test_select_ignores_override_of_other_lemma(small_repo: DictionaryRepository) -> None:
    """その見出し語の語義でない上書き指定は使わない(ignoredSenseOverrides になる)。"""
    choice = SenseSelector(small_repo).select(0, override="90000011-n")

    assert choice == SenseChoice("90000041-n", is_override_applied=False)


def test_select_without_sense_is_integrity_error(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_lexicon(["語"])
    monkeypatch.setattr(repo, "senses_of", lambda lemma_id: [])

    with pytest.raises(DictionaryIntegrityError, match="見出し語の語義 0"):
        SenseSelector(repo).select(0)
