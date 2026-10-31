"""五十音順リスト上でN個先の見出し語を返す(GojuonShifter、F2)。"""

from typing import Final

from s7.domain.transform import GojuonRoute, GojuonShift
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.shifter import shift_index

# 経路の間の語(neighbors)を全部入れる上限。超えたら最初と最後の3語だけにする
MAX_NEIGHBORS: Final = 6
_NEIGHBORS_EACH_SIDE: Final = MAX_NEIGHBORS // 2


class GojuonShifter:
    """五十音順S+Nで置き換える。"""

    def __init__(self, repo: DictionaryRepository) -> None:
        """変換用辞書を受け取る。"""
        self._repo = repo

    def shift(self, lemma_id: int, n: int) -> GojuonShift | None:
        """見出し語を、五十音順リスト上でN個先の見出し語にする。

        Args:
            lemma_id: 元の見出し語の番号(五十音順リスト上の位置と同じ)。
            n: いくつ先に進むか。

        Returns:
            置き換えた結果。読みの無い見出し語(五十音順リストに無い)ならNone。
        """
        size = self._repo.gojuon_lemma_count()
        if lemma_id >= size:
            return None
        to_index, wrapped = shift_index(lemma_id, n, size)
        neighbors, omitted = self._neighbors(lemma_id, n, size)
        route = GojuonRoute(
            from_index=lemma_id,
            to_index=to_index,
            wrapped=wrapped,
            neighbors=neighbors,
            neighbors_omitted=omitted,
        )
        return GojuonShift(to_lemma=self._repo.lemma(to_index), route=route)

    def _neighbors(self, lemma_id: int, n: int, size: int) -> tuple[tuple[str, ...], int]:
        """元の語と変換後の語の間にある N-1 語(機能設計書「経路の間の語」)。"""
        steps = list(range(1, n))
        omitted = max(len(steps) - MAX_NEIGHBORS, 0)
        if omitted:
            steps = steps[:_NEIGHBORS_EACH_SIDE] + steps[-_NEIGHBORS_EACH_SIDE:]
        surfaces = tuple(self._repo.lemma((lemma_id + step) % size).surface for step in steps)
        return surfaces, omitted
