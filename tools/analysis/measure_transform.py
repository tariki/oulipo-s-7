"""変換の処理の速さとメモリを測る(docs/architecture.md「設計前の検証結果」「レスポンスタイム」)。

本物の変換用辞書(data/build/s7dict.sqlite)とSudachiで、Sudachiの初期化、辞書の読み込み、
10,000文字と50,000文字の変換(両モード、N=7)の時間を測る。文章は、日本語WordNetの日本語の
定義文を概念IDの順につなげて作る(標準の文章は品質の報告の作業で用意する)。

    uv run --directory server python ../tools/analysis/measure_transform.py
"""

import resource
import sqlite3
import statistics
import time
from contextlib import closing
from pathlib import Path

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.domain.transform import Mode, NounResult
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.noun_extractor import NounExtractor
from s7.services.sense_selector import SenseSelector
from s7.services.transform_service import TransformService

ROOT = Path(__file__).resolve().parents[2]
DICTIONARY = ROOT / "data/build/s7dict.sqlite"
RUNS = 5
MAX_CHARS = 50_000


def main() -> None:
    """各段階の時間と、最大メモリを出す。"""
    started = time.perf_counter()
    tokenizer = SudachiTokenizer()
    tokenizer.tokenize("初期化", "A")  # 辞書の読み込みを終わらせる
    print(f"Sudachiの初期化: {time.perf_counter() - started:.2f}秒 / 最大メモリ {_max_rss_mb()}MB")

    started = time.perf_counter()
    repo = DictionaryRepository.load(DICTIONARY)
    elapsed = time.perf_counter() - started
    print(f"変換用辞書の読み込み: {elapsed:.2f}秒 / 最大メモリ {_max_rss_mb()}MB")

    selector = SenseSelector(repo)
    service = TransformService(
        NounExtractor(tokenizer, repo),
        GojuonShifter(repo),
        ConceptShifter(repo, selector),
        repo.meta().dictionary_version,
    )
    source = _sample_text()
    for chars in (10_000, MAX_CHARS):
        text = source[:chars]
        for mode in ("gojuon", "concept"):
            _measure(service, text, mode)
    print(f"最大メモリ(全体): {_max_rss_mb()}MB")


def _measure(service: TransformService, text: str, mode: Mode) -> None:
    service.transform(text, mode, 7)  # 1回目は捨てる
    times = []
    for _ in range(RUNS):
        started = time.perf_counter()
        result = service.transform(text, mode, 7)
        times.append(time.perf_counter() - started)
    nouns = [s for s in result.segments if isinstance(s, NounResult)]
    rate = result.meta.replaced_count / len(nouns) if nouns else 0
    print(
        f"{len(text):>6}文字 {mode:<7}: 中央値 {statistics.median(times):.2f}秒"
        f"(最大 {max(times):.2f}秒) 名詞 {len(nouns)} 置換率 {rate:.1%}"
    )


def _sample_text() -> str:
    with closing(sqlite3.connect(f"{DICTIONARY.as_uri()}?mode=ro", uri=True)) as connection:
        rows = connection.execute(
            "SELECT definition_ja FROM synset WHERE definition_ja IS NOT NULL ORDER BY id"
        )
        text = ""
        for (definition,) in rows:
            text += definition + "。"
            if len(text) > MAX_CHARS:
                return text
    return text


def _max_rss_mb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024


if __name__ == "__main__":
    main()
