"""日本語WordNetとSudachiから変換用辞書を作る(DictionaryBuilder)。

機能設計書「辞書ビルダー」の処理を順に呼ぶ。
"""

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

from s7.adapters.tokenizer import Tokenizer
from s7.domain.dictionary import DictionaryMeta, Lemma, Sense
from s7.services.gojuon_collation import compute_sort_key
from s7builder.build_report import BuildReport
from s7builder.dictionary_writer import DictionaryContents, write_dictionary
from s7builder.lemma_filter import filter_lemmas, read_excluded_lemmas
from s7builder.reading_assigner import Reading, ReadingAssigner
from s7builder.sense_ranker import rank_senses
from s7builder.sibling_indexer import check_integrity, index_siblings
from s7builder.version import DICTIONARY_DATE, DICTIONARY_VERSION, WORDNET_VERSION
from s7builder.wordnet_reader import read_wordnet


class DictionaryBuilder:
    """変換用辞書を作る。"""

    def __init__(
        self, tokenizer: Tokenizer, sudachidict_version: str, wordnet_license: str
    ) -> None:
        """ビルドに使う部品を受け取る。

        Args:
            tokenizer: 読みの決定に使う形態素解析。
            sudachidict_version: 読みの決定に使うSudachiDict(例: "core-20261015")。
            wordnet_license: 日本語WordNetのライセンス全文(変換用辞書の meta に入れる)。
        """
        self._assigner = ReadingAssigner(tokenizer)
        self._sudachidict_version = sudachidict_version
        self._wordnet_license = wordnet_license

    def build(self, wordnet_db: Path, excluded_lemmas: Path, output: Path) -> BuildReport:
        """変換用辞書を作って書き出す。

        Args:
            wordnet_db: 日本語WordNet(wnjpn.db)。
            excluded_lemmas: 置換先から除外する語のリスト。
            output: 変換用辞書の出力先。

        Returns:
            ビルドの報告。

        Raises:
            BuildError: 入力が無い・不正、または整合性の検査に失敗したとき。
        """
        # リストの入れ忘れに早く気付くよう、大きな元データより先に読む
        excluded = read_excluded_lemmas(excluded_lemmas)
        wordnet = read_wordnet(wordnet_db)
        filtered = filter_lemmas(wordnet.lemma_synsets, excluded)
        readings = {surface: self._assigner.assign(surface) for surface in filtered.kept}
        lemmas = order_lemmas(readings)
        senses = [
            sense
            for lemma in lemmas
            for sense in rank_senses(
                lemma.id, wordnet.lemma_synsets[lemma.surface], wordnet.english_frequencies
            )
        ]
        tree = index_siblings(wordnet, _lemma_ids_by_synset(senses))
        check_integrity(tree, senses)
        meta = DictionaryMeta(
            dictionary_version=DICTIONARY_VERSION,
            wordnet_version=WORDNET_VERSION,
            sudachidict_version=self._sudachidict_version,
            built_at=DICTIONARY_DATE,
            lemma_count=len(lemmas),
            gojuon_lemma_count=sum(lemma.reading is not None for lemma in lemmas),
            synset_count=len(tree.synsets),
        )
        write_dictionary(
            DictionaryContents(
                lemmas=lemmas,
                synsets=tree.synsets,
                sibling_groups=tree.sibling_groups,
                senses=senses,
                meta=meta,
                wordnet_license=self._wordnet_license,
            ),
            output,
        )
        sources = [reading.source for reading in readings.values() if reading is not None]
        return BuildReport(
            meta=meta,
            wordnet_lemma_count=len(wordnet.lemma_synsets),
            excluded_list_size=filtered.excluded_list_size,
            excluded_lemma_count=filtered.excluded_lemma_count,
            reading_by_kana_count=sources.count("kana"),
            reading_by_sudachi_count=sources.count("sudachi"),
            no_reading_count=meta.lemma_count - meta.gojuon_lemma_count,
            sibling_group_count=len(tree.sibling_groups),
        )


def order_lemmas(readings: Mapping[str, Reading | None]) -> list[Lemma]:
    """見出し語を並べて Lemma.id を決める。

    読みのある語を (sort_key, 表記) の順に並べ、その後ろに読みの無い語を表記の順に並べる
    (機能設計書「Lemma」の並び順)。id が 0〜(読みのある語の数 - 1) の語が五十音順リストになる。

    Args:
        readings: 表記 → 読み(決まらなければNone)。

    Returns:
        id の順の見出し語。
    """
    with_reading = sorted(
        (compute_sort_key(reading.reading), surface, reading.reading)
        for surface, reading in readings.items()
        if reading is not None
    )
    without_reading = sorted(surface for surface, reading in readings.items() if reading is None)
    ordered = [(surface, reading, key) for key, surface, reading in with_reading] + [
        (surface, None, None) for surface in without_reading
    ]
    return [
        Lemma(id=index, surface=surface, reading=reading, sort_key=key)
        for index, (surface, reading, key) in enumerate(ordered)
    ]


def _lemma_ids_by_synset(senses: list[Sense]) -> dict[str, list[int]]:
    lemma_ids: defaultdict[str, list[int]] = defaultdict(list)
    for sense in senses:
        lemma_ids[sense.synset_id].append(sense.lemma_id)
    return dict(lemma_ids)
