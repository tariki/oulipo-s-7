from s7.domain.dictionary import Sense
from s7builder.sense_ranker import rank_senses


def test_rank_senses_orders_by_score_then_synset_id() -> None:
    # Given: 99000003 と 99000001 が同点、99000002 はスコアが無い(0)
    scores = {"99000001-n": 5, "99000003-n": 5, "99000004-n": 9}

    # When
    senses = rank_senses(7, ["99000003-n", "99000002-n", "99000001-n", "99000004-n"], scores)

    # Then
    assert senses == [
        Sense(lemma_id=7, synset_id="99000004-n", score=9, rank=0),
        Sense(lemma_id=7, synset_id="99000001-n", score=5, rank=1),
        Sense(lemma_id=7, synset_id="99000003-n", score=5, rank=2),
        Sense(lemma_id=7, synset_id="99000002-n", score=0, rank=3),
    ]
