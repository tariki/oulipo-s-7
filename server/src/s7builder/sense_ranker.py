"""見出し語の語義に順位を付ける(SenseRanker)。

機能設計書「3. 語義の選択」の実装。
"""

from collections.abc import Mapping, Sequence

from s7.domain.dictionary import Sense


def rank_senses(lemma_id: int, synset_ids: Sequence[str], scores: Mapping[str, int]) -> list[Sense]:
    """1つの見出し語の語義を、スコアの大きい順(同じなら概念IDの順)に並べる。

    Args:
        lemma_id: 見出し語の番号。
        synset_ids: その見出し語の語義の概念ID。
        scores: 概念ID → スコア(英語の語義頻度の合計)。無い概念は0。

    Returns:
        順位(rank)を付けた語義。rank の順。
    """
    ordered = sorted(synset_ids, key=lambda synset_id: (-scores.get(synset_id, 0), synset_id))
    return [
        Sense(lemma_id=lemma_id, synset_id=synset_id, score=scores.get(synset_id, 0), rank=rank)
        for rank, synset_id in enumerate(ordered)
    ]
