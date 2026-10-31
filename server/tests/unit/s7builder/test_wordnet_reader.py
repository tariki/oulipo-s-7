from pathlib import Path

import pytest
from fixtures.sample_wordnet import create_sample_wordnet

from s7builder.errors import BuildError
from s7builder.wordnet_reader import WordNetData, read_wordnet


@pytest.fixture(scope="module")
def wordnet(tmp_path_factory: pytest.TempPathFactory) -> WordNetData:
    return read_wordnet(create_sample_wordnet(tmp_path_factory.mktemp("wn") / "wnjpn.db"))


def test_read_wordnet_reads_only_japanese_nouns(wordnet: WordNetData) -> None:
    # 動詞の「走る」は入らない。重なった語義の行は1つにまとまる
    assert "走る" not in wordnet.lemma_synsets
    assert wordnet.lemma_synsets["実体"] == ("90000001-n",)
    assert wordnet.lemma_synsets["猫"] == ("90000011-n", "90000040-n")
    assert list(wordnet.lemma_synsets) == sorted(wordnet.lemma_synsets)


def test_read_wordnet_reads_noun_synsets_and_parent_links(wordnet: WordNetData) -> None:
    # 動詞の概念と、hype・inst 以外の関係(hypo、hasi)は入らない
    assert "90000099-v" not in wordnet.synset_ids
    assert len(wordnet.synset_ids) == 15
    assert wordnet.parent_candidates["90000030-n"] == (
        ("90000003-n", "hypernym"),
        ("90000031-n", "instance_hypernym"),
    )
    assert "90000001-n" not in wordnet.parent_candidates


def test_read_wordnet_picks_shortest_definition_per_sid(wordnet: WordNetData) -> None:
    """同じ sid の行が複数あれば最も短い版を使い、sid の順につなぐ。"""
    assert wordnet.definitions_en["90000011-n"] == "feline; pet"
    assert wordnet.definitions_ja["90000011-n"] == "ネコ科の動物；家で飼われる"
    assert "90000012-n" not in wordnet.definitions_en  # 空白だけの定義文
    assert wordnet.definitions_ja["90000012-n"] == "イヌ科の動物"  # 別の sid の同じ文は1回だけ


def test_read_wordnet_sums_english_frequencies(wordnet: WordNetData) -> None:
    assert wordnet.english_frequencies["90000011-n"] == 5
    assert wordnet.english_frequencies["90000013-n"] == 0  # freq が NULL


def test_read_wordnet_rejects_file_that_is_not_wordnet(tmp_path: Path) -> None:
    # Given: SQLiteではないファイル
    path = tmp_path / "wnjpn.db"
    path.write_bytes(b"not a database")

    # When / Then
    with pytest.raises(BuildError, match="日本語WordNetとして読めません"):
        read_wordnet(path)
