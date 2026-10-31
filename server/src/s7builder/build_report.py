"""ビルドの報告(data/reports/build-report.json)。

辞書を変えたときの影響を差分で確かめるため、コミットする。毎回変わる値(時刻など)は入れない。
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from s7.domain.dictionary import DictionaryMeta


@dataclass(frozen=True, slots=True)
class BuildReport:
    """ビルドの報告。

    Attributes:
        meta: 変換用辞書のメタ情報。
        wordnet_lemma_count: 日本語WordNetの名詞の見出し語の数。
        excluded_list_size: 置換先から除外する語のリストの語数。
        excluded_lemma_count: リストにより実際に除外した見出し語の数。
        reading_by_kana_count: かなだけの表記から読みを決めた数。
        reading_by_sudachi_count: Sudachiで読みを決めた数。
        no_reading_count: 読みが決まらなかった数(概念版だけで使う)。
        sibling_group_count: 兄弟グループの数。
    """

    meta: DictionaryMeta
    wordnet_lemma_count: int
    excluded_list_size: int
    excluded_lemma_count: int
    reading_by_kana_count: int
    reading_by_sudachi_count: int
    no_reading_count: int
    sibling_group_count: int


def write_build_report(report: BuildReport, path: Path) -> None:
    """報告をJSONで書く。キーを並べ替え、差分を読みやすくする。

    Args:
        report: ビルドの報告。
        path: 出力先のパス。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)
    # 途中で失敗しても前の報告を壊さないよう、一時ファイルに書いてから置き換える
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text + "\n", encoding="utf-8")
    temporary.replace(path)
