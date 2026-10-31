import re
from pathlib import Path

import pytest

from s7.services.formal_nouns import FORMAL_NOUNS

DOCS = Path(__file__).resolve().parents[5] / "docs"


def _copy_in(document: str, after: str) -> list[str]:
    """ドキュメントの見出し(after)の後にある最初のコードブロックから、「、」区切りの一覧を読む。"""
    text = (DOCS / document).read_text(encoding="utf-8")
    section = text[text.index(after) :]
    match = re.search(r"```\n(.+?)\n```", section, re.DOTALL)
    assert match is not None
    return match.group(1).strip().split("、")


@pytest.mark.parametrize(
    ("document", "after"),
    [
        ("functional-design.md", "**形式名詞**"),
        ("glossary.md", "### 形式名詞"),
    ],
)
def test_formal_nouns_match_copies_in_docs(document: str, after: str) -> None:
    """機能設計書と用語集の写しが、正(formal_nouns.py)と一致する。"""
    copy = _copy_in(document, after)

    assert len(copy) == len(set(copy))
    assert set(copy) == FORMAL_NOUNS


def test_formal_nouns_are_hiragana_only() -> None:
    """漢字の表記(「事」「物」など)は実質的な意味で使われることが多いため、リストに入れない。"""
    assert all(re.fullmatch(r"[ぁ-ゖ]+", word) for word in FORMAL_NOUNS)
