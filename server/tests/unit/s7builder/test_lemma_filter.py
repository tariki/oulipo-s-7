from pathlib import Path

import pytest

from s7builder.errors import BuildError
from s7builder.lemma_filter import filter_lemmas, read_excluded_lemmas


def test_read_excluded_lemmas_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "excluded.txt"
    path.write_text("# 見出し\n\n  語A  \n語B # 理由\n語A\n", encoding="utf-8")

    # When
    words = read_excluded_lemmas(path)

    # Then
    assert words == {"語A", "語B"}


def test_read_excluded_lemmas_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(BuildError, match="ありません"):
        read_excluded_lemmas(tmp_path / "missing.txt")


@pytest.mark.parametrize("content", ["", "\n\n", "# コメントだけ\n   # これも\n"])
def test_read_excluded_lemmas_without_words_fails(tmp_path: Path, content: str) -> None:
    # Given
    path = tmp_path / "excluded.txt"
    path.write_text(content, encoding="utf-8")

    # When / Then
    with pytest.raises(BuildError, match="語がありません"):
        read_excluded_lemmas(path)


def test_filter_lemmas_removes_listed_surfaces_and_counts() -> None:
    # Given: リストの「語Z」は見出し語に無い
    excluded = frozenset({"語B", "語Z"})

    # When
    result = filter_lemmas(["語C", "語B", "語A"], excluded)

    # Then
    assert result.kept == ("語A", "語C")
    assert result.excluded_list_size == 2
    assert result.excluded_lemma_count == 1
