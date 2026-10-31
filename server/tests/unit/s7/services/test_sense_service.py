import pytest

from s7.domain.errors import LemmaNotFoundError
from s7.domain.transform import SenseItem
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.sense_service import SenseService


def test_list_senses_in_rank_order(small_repo: DictionaryRepository) -> None:
    result = SenseService(small_repo).list_senses("猫")

    assert result.lemma == "猫"
    assert result.senses == (
        SenseItem("90000011-n", 0, "ネコ科の動物；家で飼われる", ("ネコ", "猫")),
        SenseItem("90000040-n", 1, None, ("猫",)),
    )


def test_list_senses_uses_exact_surface(small_repo: DictionaryRepository) -> None:
    """表記の完全一致で引く(正規化しない)。"""
    with pytest.raises(LemmaNotFoundError):
        SenseService(small_repo).list_senses("ねこ")


def test_list_senses_of_excluded_lemma_is_not_found(small_repo: DictionaryRepository) -> None:
    with pytest.raises(LemmaNotFoundError):
        SenseService(small_repo).list_senses("禁止語")
