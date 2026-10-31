from collections.abc import Mapping

import pytest

from s7.domain.dictionary import ParentRelation, Sense, SiblingGroup, Synset
from s7builder.errors import BuildError
from s7builder.sibling_indexer import ConceptTree, check_integrity, index_siblings
from s7builder.wordnet_reader import WordNetData


def _wordnet(
    synset_ids: list[str],
    parents: Mapping[str, tuple[tuple[str, ParentRelation], ...]],
) -> WordNetData:
    return WordNetData(
        lemma_synsets={},
        synset_ids=tuple(sorted(synset_ids)),
        parent_candidates=parents,
        definitions_ja={"90000001-n": "根の定義"},
        definitions_en={"90000001-n": "root"},
        english_frequencies={},
    )


def test_index_siblings_chooses_smallest_parent_id() -> None:
    # Given: 上位語が2つ(hype の 90000003 と inst の 90000002)
    wordnet = _wordnet(
        ["90000001-n", "90000002-n", "90000003-n"],
        {"90000001-n": (("90000002-n", "instance_hypernym"), ("90000003-n", "hypernym"))},
    )

    # When
    tree = index_siblings(wordnet, {})

    # Then
    root = tree.synsets[0]
    assert (root.parent_id, root.parent_relation) == ("90000002-n", "instance_hypernym")


def test_index_siblings_prefers_hypernym_for_same_parent() -> None:
    wordnet = _wordnet(
        ["90000001-n", "90000002-n"],
        {"90000001-n": (("90000002-n", "hypernym"), ("90000002-n", "instance_hypernym"))},
    )

    tree = index_siblings(wordnet, {})

    assert tree.synsets[0].parent_relation == "hypernym"


def test_index_siblings_builds_groups_ordered_by_representative() -> None:
    # Given: 親 90000001 の子が4つ。90000013 は見出し語が無い(除外で無くなった場合も同じ)
    parent: tuple[tuple[str, ParentRelation], ...] = (("90000001-n", "hypernym"),)
    wordnet = _wordnet(
        ["90000001-n", "90000011-n", "90000012-n", "90000013-n", "90000014-n"],
        {
            "90000011-n": parent,
            "90000012-n": parent,
            "90000013-n": parent,
            "90000014-n": parent,
        },
    )
    lemma_ids = {"90000001-n": [0], "90000011-n": [5, 2], "90000012-n": [1], "90000014-n": [2]}

    # When
    tree = index_siblings(wordnet, lemma_ids)

    # Then: 代表語の Lemma.id → 概念ID の順。親は上位語が無いためグループに入らない
    assert tree.sibling_groups == (
        SiblingGroup(
            id=0, parent_id="90000001-n", member_ids=("90000012-n", "90000011-n", "90000014-n")
        ),
    )
    by_id = {s.id: s for s in tree.synsets}
    assert by_id["90000011-n"].representative_lemma_id == 2
    assert (by_id["90000014-n"].sibling_group_id, by_id["90000014-n"].sibling_index) == (0, 2)
    assert by_id["90000013-n"] == Synset(
        id="90000013-n",
        parent_id="90000001-n",
        parent_relation="hypernym",
        sibling_group_id=None,
        sibling_index=None,
        representative_lemma_id=None,
        definition_ja=None,
        definition_en=None,
    )
    assert (by_id["90000001-n"].definition_ja, by_id["90000001-n"].definition_en) == (
        "根の定義",
        "root",
    )


def test_index_siblings_numbers_groups_by_parent_id() -> None:
    wordnet = _wordnet(
        ["90000001-n", "90000002-n", "90000011-n", "90000021-n"],
        {"90000011-n": (("90000002-n", "hypernym"),), "90000021-n": (("90000001-n", "hypernym"),)},
    )

    tree = index_siblings(wordnet, {"90000011-n": [0], "90000021-n": [1]})

    assert [(g.id, g.parent_id) for g in tree.sibling_groups] == [
        (0, "90000001-n"),
        (1, "90000002-n"),
    ]


def _synset(synset_id: str, parent_id: str | None) -> Synset:
    return Synset(
        synset_id, parent_id, "hypernym" if parent_id else None, None, None, None, None, None
    )


@pytest.mark.parametrize(
    ("tree", "senses", "role"),
    [
        (ConceptTree((_synset("90000001-n", "99999999-n"),), ()), [], "上位語"),
        (
            ConceptTree(
                (_synset("90000001-n", None),), (SiblingGroup(0, "99999999-n", ("90000001-n",)),)
            ),
            [],
            "兄弟グループの上位語",
        ),
        (
            ConceptTree(
                (_synset("90000001-n", None),), (SiblingGroup(0, "90000001-n", ("99999999-n",)),)
            ),
            [],
            "兄弟グループのメンバー",
        ),
        (ConceptTree((_synset("90000001-n", None),), ()), [Sense(0, "99999999-n", 0, 0)], "語義"),
    ],
)
def test_check_integrity_rejects_unknown_synset(
    tree: ConceptTree, senses: list[Sense], role: str
) -> None:
    with pytest.raises(BuildError, match=f"^{role}の概念 99999999-n"):
        check_integrity(tree, senses)


def test_check_integrity_accepts_consistent_tree() -> None:
    tree = ConceptTree(
        (_synset("90000001-n", None), _synset("90000002-n", "90000001-n")),
        (SiblingGroup(0, "90000001-n", ("90000002-n",)),),
    )

    check_integrity(tree, [Sense(0, "90000002-n", 0, 0)])
