"""置換先から除外する語のリストを見出し語に適用する(LemmaFilter)。

PRDの「置換先から除外する語」。リストに載っている表記は見出し語に含めない。
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from s7builder.errors import BuildError


@dataclass(frozen=True, slots=True)
class FilterResult:
    """除外の結果。

    Attributes:
        kept: 残った見出し語の表記(文字コード順)。
        excluded_list_size: リストの語数。
        excluded_lemma_count: リストにより実際に除外した見出し語の数。
    """

    kept: tuple[str, ...]
    excluded_list_size: int
    excluded_lemma_count: int


def read_excluded_lemmas(path: Path) -> frozenset[str]:
    """除外リストを読む。1行1語で、# 以降はコメント。前後の空白と空行は無視する。

    Args:
        path: リストのファイル(data/excluded-lemmas.txt)。

    Returns:
        除外する表記の集合。

    Raises:
        BuildError: ファイルが無い、または1語も無いとき(リストを入れ忘れたまま公開しないため)。
    """
    if not path.is_file():
        raise BuildError(f"置換先から除外する語のリストがありません: {path}")
    words = frozenset(
        word
        for line in path.read_text(encoding="utf-8").splitlines()
        if (word := line.split("#", 1)[0].strip())
    )
    if not words:
        raise BuildError(f"置換先から除外する語のリストに語がありません: {path}")
    return words


def filter_lemmas(surfaces: Iterable[str], excluded: frozenset[str]) -> FilterResult:
    """見出し語から、除外リストに載っている表記を取り除く。

    Args:
        surfaces: 日本語WordNetの名詞の見出し語の表記。
        excluded: 除外する表記。

    Returns:
        除外の結果。
    """
    all_surfaces = sorted(set(surfaces))
    kept = tuple(s for s in all_surfaces if s not in excluded)
    return FilterResult(
        kept=kept,
        excluded_list_size=len(excluded),
        excluded_lemma_count=len(all_surfaces) - len(kept),
    )
