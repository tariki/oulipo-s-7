"""見出し語の語義から使う1つを選ぶ(SenseSelector、機能設計書「3. 語義の選択」)。"""

from s7.domain.errors import DictionaryIntegrityError
from s7.domain.transform import SenseChoice
from s7.repositories.dictionary_repository import DictionaryRepository


class SenseSelector:
    """語義を選ぶ。"""

    def __init__(self, repo: DictionaryRepository) -> None:
        """変換用辞書を受け取る。"""
        self._repo = repo

    def select(self, lemma_id: int, override: str | None = None) -> SenseChoice:
        """使う語義を選ぶ。

        Args:
            lemma_id: 見出し語の番号。
            override: 語義の上書き指定(F8)の概念ID。

        Returns:
            選んだ語義。上書きがその見出し語の語義なら上書きを、そうでなければ順位0の語義を使う。

        Raises:
            DictionaryIntegrityError: 見出し語に語義が無いとき(読み込み時に検査するため起きない)。
        """
        senses = self._repo.senses_of(lemma_id)
        if not senses:
            raise DictionaryIntegrityError(str(lemma_id), kind="見出し語の語義")
        if override is not None and any(s.synset_id == override for s in senses):
            return SenseChoice(synset_id=override, is_override_applied=True)
        return SenseChoice(synset_id=senses[0].synset_id, is_override_applied=False)
