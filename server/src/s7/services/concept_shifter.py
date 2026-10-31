"""兄弟グループの中でN個先の概念の代表語を返す(ConceptShifter、F3)。

機能設計書「4. 概念版S+N」ステップ3の実装。
"""

from s7.domain.dictionary import Lemma, Synset
from s7.domain.errors import DictionaryIntegrityError
from s7.domain.transform import (
    ConceptRef,
    ConceptRoute,
    ConceptShift,
    ConceptShiftResult,
    ConceptStep,
    SenseChoice,
)
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.sense_selector import SenseSelector
from s7.services.shifter import shift_index

# 兄弟グループの大きさがこれ未満(自分だけ)なら、1つ上の階層に上がる
_MIN_GROUP_SIZE = 2


class ConceptShifter:
    """概念版S+Nで置き換える。"""

    def __init__(self, repo: DictionaryRepository, selector: SenseSelector) -> None:
        """変換用辞書と、語義の選び方を受け取る。"""
        self._repo = repo
        self._selector = selector

    def shift(
        self, lemma_id: int, n: int, synset_override: str | None = None
    ) -> ConceptShiftResult:
        """見出し語の語義を選び、兄弟グループでN個先の概念の代表語にする。

        Args:
            lemma_id: 元の見出し語の番号。読みが無くてもよい。
            n: いくつ先に進むか。
            synset_override: 語義の上書き指定(F8)。

        Returns:
            選んだ語義と、置き換えた結果(最上位まで兄弟が無ければ shift はNone)。
        """
        sense = self._selector.select(lemma_id, synset_override)
        return ConceptShiftResult(
            sense=sense, shift=self._shift_from(self._synset(sense.synset_id), n)
        )

    def select_sense(self, lemma_id: int, synset_override: str | None = None) -> SenseChoice:
        """置き換えずに語義だけを選ぶ(除外された名詞の語義を示すため)。"""
        return self._selector.select(lemma_id, synset_override)

    def _shift_from(self, start: Synset, n: int) -> ConceptShift | None:
        current = start
        climbs: list[ConceptStep] = []
        while True:
            if current.sibling_group_id is not None and current.sibling_index is not None:
                group = self._repo.sibling_group(current.sibling_group_id)
                if len(group.member_ids) >= _MIN_GROUP_SIZE:
                    to_index, wrapped = shift_index(current.sibling_index, n, len(group.member_ids))
                    to = self._synset(group.member_ids[to_index])
                    route = ConceptRoute(
                        climbs=tuple(climbs),
                        parent=self._ref(self._synset(group.parent_id)),
                        from_=self._ref(current),
                        to=self._ref(to),
                        group_size=len(group.member_ids),
                        wrapped=wrapped,
                    )
                    return ConceptShift(to_lemma=self._representative(to), route=route)
            if current.parent_id is None:
                return None  # 最上位まで兄弟が無い(no_sibling)
            if current.parent_relation is None:
                raise DictionaryIntegrityError(current.id, kind="上位語の関係が無い概念")
            # 上がった先が代表語を持たなければ兄弟グループに入っていないため、さらに上がる
            parent = self._synset(current.parent_id)
            climbs.append(
                ConceptStep(self._ref(current), self._ref(parent), current.parent_relation)
            )
            current = parent

    def _synset(self, synset_id: str) -> Synset:
        synset = self._repo.synset(synset_id)
        if synset is None:
            raise DictionaryIntegrityError(
                synset_id
            )  # 読み込み時に検査するため、起きたら辞書の不備
        return synset

    def _representative(self, synset: Synset) -> Lemma:
        if synset.representative_lemma_id is None:
            raise DictionaryIntegrityError(synset.id, kind="代表語の無い兄弟")
        return self._repo.lemma(synset.representative_lemma_id)

    def _ref(self, synset: Synset) -> ConceptRef:
        """置換経路に表示する形にする(代表語と、日本語が無ければ英語の定義文)。"""
        rep = synset.representative_lemma_id
        return ConceptRef(
            synset_id=synset.id,
            lemma=None if rep is None else self._repo.lemma(rep).surface,
            definition=synset.definition_ja or synset.definition_en,
        )
