"""上位語・代表語・兄弟グループを決める(SiblingIndexer)。

機能設計書「4. 概念版S+N」のステップ1・2(ビルド時)の実装。
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from s7.domain.dictionary import ParentRelation, Sense, SiblingGroup, Synset
from s7builder.errors import BuildError
from s7builder.wordnet_reader import WordNetData


@dataclass(frozen=True, slots=True)
class ConceptTree:
    """概念と兄弟グループ。

    Attributes:
        synsets: 名詞の概念(概念IDの順)。
        sibling_groups: 兄弟グループ(id の順)。
    """

    synsets: tuple[Synset, ...]
    sibling_groups: tuple[SiblingGroup, ...]


def index_siblings(wordnet: WordNetData, lemma_ids: Mapping[str, Sequence[int]]) -> ConceptTree:
    """概念ごとに上位語と代表語を決め、兄弟グループを作る。

    Args:
        wordnet: 日本語WordNetから読んだデータ。
        lemma_ids: 概念ID → その概念を語義に持つ見出し語の Lemma.id(除外した語を含まない)。

    Returns:
        概念と兄弟グループ。
    """
    parents = {
        synset_id: _choose_parent(wordnet.parent_candidates.get(synset_id, ()))
        for synset_id in wordnet.synset_ids
    }
    representatives = {
        synset_id: min(lemma_ids[synset_id])
        for synset_id in wordnet.synset_ids
        if lemma_ids.get(synset_id)
    }
    groups = _make_groups(parents, representatives)
    positions = {
        member: (group.id, index)
        for group in groups
        for index, member in enumerate(group.member_ids)
    }
    synsets = tuple(
        Synset(
            id=synset_id,
            parent_id=parent[0] if (parent := parents[synset_id]) else None,
            parent_relation=parent[1] if parent else None,
            sibling_group_id=position[0] if (position := positions.get(synset_id)) else None,
            sibling_index=position[1] if position else None,
            representative_lemma_id=representatives.get(synset_id),
            definition_ja=wordnet.definitions_ja.get(synset_id),
            definition_en=wordnet.definitions_en.get(synset_id),
        )
        for synset_id in wordnet.synset_ids
    )
    return ConceptTree(synsets=synsets, sibling_groups=groups)


def _choose_parent(
    candidates: Sequence[tuple[str, ParentRelation]],
) -> tuple[str, ParentRelation] | None:
    """概念IDが最小の上位語を選ぶ。同じ概念が両方の関係で現れたら hypernym(文字列順で先)。"""
    return min(candidates) if candidates else None


def _make_groups(
    parents: Mapping[str, tuple[str, ParentRelation] | None], representatives: Mapping[str, int]
) -> tuple[SiblingGroup, ...]:
    """代表語と上位語を持つ概念を上位語ごとにまとめ、上位語の概念IDの順に番号を振る。"""
    members: defaultdict[str, list[str]] = defaultdict(list)
    for synset_id, parent in parents.items():
        if parent is not None and synset_id in representatives:
            members[parent[0]].append(synset_id)
    return tuple(
        SiblingGroup(
            id=group_id,
            parent_id=parent_id,
            member_ids=tuple(sorted(members[parent_id], key=lambda s: (representatives[s], s))),
        )
        for group_id, parent_id in enumerate(sorted(members))
    )


def check_integrity(tree: ConceptTree, senses: Iterable[Sense]) -> None:
    """上位語・兄弟グループのメンバー・語義の概念が、すべて概念として存在するかを確かめる。

    実行時の ConceptShifter は、この検査が通った辞書を前提にする(機能設計書「4. 概念版S+N」)。

    Args:
        tree: 概念と兄弟グループ。
        senses: すべての語義。

    Raises:
        BuildError: 存在しない概念を指していたとき。メッセージには概念IDだけを入れる。
    """
    known = {synset.id for synset in tree.synsets}
    referenced = [
        *(("上位語", s.parent_id) for s in tree.synsets if s.parent_id is not None),
        *(("兄弟グループの上位語", g.parent_id) for g in tree.sibling_groups),
        *(("兄弟グループのメンバー", m) for g in tree.sibling_groups for m in g.member_ids),
        *(("語義", sense.synset_id) for sense in senses),
    ]
    for role, synset_id in referenced:
        if synset_id not in known:
            raise BuildError(f"{role}の概念 {synset_id} が概念の一覧にありません")
