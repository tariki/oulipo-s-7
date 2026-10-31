"""見出し語の語義の一覧を作る(SenseService、[P1: F8])。"""

from s7.domain.errors import LemmaNotFoundError
from s7.domain.transform import SenseItem, SenseList
from s7.repositories.dictionary_repository import DictionaryRepository


class SenseService:
    """語義の一覧。"""

    def __init__(self, repo: DictionaryRepository) -> None:
        """変換用辞書を受け取る。"""
        self._repo = repo

    def list_senses(self, lemma: str) -> SenseList:
        """見出し語の語義を、順位の順に、定義文とその概念の見出し語つきで返す。

        Args:
            lemma: 見出し語の表記。完全一致で引く(正規化しない)。

        Returns:
            語義の一覧。

        Raises:
            LemmaNotFoundError: 見出し語が辞書に無いとき。
        """
        found = self._repo.find_lemma(lemma)
        if found is None:
            raise LemmaNotFoundError
        items = []
        for sense in self._repo.senses_of(found.id):
            synset = self._repo.synset(sense.synset_id)
            definition = None if synset is None else synset.definition_ja or synset.definition_en
            lemmas = tuple(x.surface for x in self._repo.lemmas_of_synset(sense.synset_id))
            items.append(SenseItem(sense.synset_id, sense.rank, definition, lemmas))
        return SenseList(lemma=found.surface, senses=tuple(items))
