"""品質の報告(data/reports/quality-report.json)。QualityReporter。

作った変換用辞書で、標準の文章3本(data/standard-texts/)を両モード・N=7で変換し、置換率を記録する
(PRDの品質指標「辞書の品質の基準」)。辞書を変えたときの影響を差分で確かめるため、コミットする。
毎回変わる値(時刻など)は入れない。

辞書ビルダーの中で、変換の処理(s7.services、s7.adapters)に依存してよいのはこのモジュールだけ
(docs/repository-structure.md「依存関係のルール」)。
"""

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from s7.adapters.tokenizer import Tokenizer
from s7.domain.transform import Mode, TransformResult
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.noun_extractor import NounExtractor
from s7.services.sense_selector import SenseSelector
from s7.services.transform_service import TransformService

#: 品質の報告で使うN(画面とAPIの既定値)。
QUALITY_N: Final = 7

#: 置換率が基準値からこれ以上下がったら知らせる(百分率のポイント。PRDの「辞書の品質の基準」)。
DROP_THRESHOLD: Final = 5.0

_MODES: Final[tuple[Mode, ...]] = ("gojuon", "concept")


@dataclass(frozen=True, slots=True)
class ModeQuality:
    """1つのモードでの結果。

    Attributes:
        noun_count: 名詞の数(辞書に無い語を含む)。
        replaced_count: 置き換えた名詞の数(replaced と climbed)。
        replaced_rate: 置換率(百分率、小数2桁)。名詞が無ければ0。
    """

    noun_count: int
    replaced_count: int
    replaced_rate: float


@dataclass(frozen=True, slots=True)
class TextQuality:
    """標準の文章1本の結果。

    Attributes:
        name: 文章の名前(ファイル名から拡張子を除いたもの)。
        chars: 本文の文字数(コードポイント数。冒頭の出典を除く)。
        gojuon: 五十音順の結果。
        concept: 概念版の結果。
    """

    name: str
    chars: int
    gojuon: ModeQuality
    concept: ModeQuality


@dataclass(frozen=True, slots=True)
class QualityReport:
    """品質の報告。

    Attributes:
        dictionary_version: 変換用辞書のバージョン。
        n: 変換に使ったN。
        texts: 文章ごとの結果(名前の順)。
    """

    dictionary_version: str
    n: int
    texts: tuple[TextQuality, ...]


def read_standard_text(path: Path) -> str:
    """標準の文章の本文を読む。冒頭の '#' で始まる行(出典)と、その直後の空行は除く。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = 0
    while start < len(lines) and lines[start].startswith("#"):
        start += 1
    while start < len(lines) and lines[start] == "":
        start += 1
    return "\n".join(lines[start:])


def list_standard_texts(texts_dir: Path) -> list[tuple[str, str]]:
    """標準の文章の名前と本文を、名前の順に返す(`*.txt` だけ)。"""
    return [(path.stem, read_standard_text(path)) for path in sorted(texts_dir.glob("*.txt"))]


class QualityReporter:
    """作った変換用辞書で標準の文章を変換し、置換率を数える。"""

    def __init__(self, tokenizer: Tokenizer) -> None:
        """名詞の抽出に使う Tokenizer を受け取る(本物は SudachiTokenizer。テストで差し替える)。"""
        self._tokenizer = tokenizer

    def report(self, dictionary: Path, texts_dir: Path) -> QualityReport:
        """標準の文章を両モードで変換し、報告を作る。

        Args:
            dictionary: 変換用辞書(s7dict.sqlite)。
            texts_dir: 標準の文章のディレクトリ。

        Returns:
            品質の報告。
        """
        repo = DictionaryRepository.load(dictionary)
        version = repo.meta().dictionary_version
        # サーバー(s7/app.py の _load_services)と同じ組み立て。辞書ビルダーは s7.app に依存できない
        service = TransformService(
            NounExtractor(self._tokenizer, repo),
            GojuonShifter(repo),
            ConceptShifter(repo, SenseSelector(repo)),
            version,
        )
        texts = tuple(
            TextQuality(
                name=name,
                chars=len(text),
                gojuon=_measure(service.transform(text, "gojuon", QUALITY_N)),
                concept=_measure(service.transform(text, "concept", QUALITY_N)),
            )
            for name, text in list_standard_texts(texts_dir)
        )
        return QualityReport(dictionary_version=version, n=QUALITY_N, texts=texts)


def _measure(result: TransformResult) -> ModeQuality:
    meta = result.meta
    rate = 0.0 if meta.noun_count == 0 else meta.replaced_count / meta.noun_count * 100
    return ModeQuality(
        noun_count=meta.noun_count,
        replaced_count=meta.replaced_count,
        replaced_rate=round(rate, 2),
    )


def write_quality_report(report: QualityReport, path: Path) -> None:
    """報告をJSONで書く。キーを並べ替え、差分を読みやすくする(ビルドの報告と同じ書き方)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)
    # 途中で失敗しても前の報告を壊さないよう、一時ファイルに書いてから置き換える
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text + "\n", encoding="utf-8")
    temporary.replace(path)


def find_drops(
    report: QualityReport,
    baseline: Mapping[str, object],
    threshold: float = DROP_THRESHOLD,
) -> list[str]:
    """置換率が基準値から threshold ポイント以上下がった値を、説明の文で返す。

    基準値の形は `{"texts": {"<名前>": {"gojuon": 率, "concept": 率}}}`。
    基準値に無い文章・モードは比べない(標準の文章を差し替えたときは、基準値もまとめて取り直すため)。

    Args:
        report: 今回の報告。
        baseline: 基準値(quality-baseline.json を読んだもの)。
        threshold: 知らせる下がり幅(ポイント)。

    Returns:
        下がった値ごとの説明。無ければ空。
    """
    texts = baseline.get("texts")
    if not isinstance(texts, Mapping):
        return []
    drops: list[str] = []
    for text in report.texts:
        base = texts.get(text.name)
        if not isinstance(base, Mapping):
            continue
        for mode in _MODES:
            base_rate = base.get(mode)
            if not isinstance(base_rate, int | float):
                continue
            rate = getattr(text, mode).replaced_rate
            if base_rate - rate >= threshold:
                drops.append(
                    f"{text.name}・{mode}: 置換率 {rate:.2f}% が基準値 {base_rate:.2f}% から"
                    f" {base_rate - rate:.2f} ポイント下がりました"
                )
    return drops
