"""兄弟グループの大きさと、上位語が複数ある概念の数を測る(docs/architecture.md「設計前の検証結果」)。

作った変換用辞書(data/build/s7dict.sqlite)と日本語WordNet(data/source/wnjpn.db)を読む。

    uv run --directory server python ../tools/analysis/measure_sibling_groups.py
"""

import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUCKETS = [("兄弟が自分だけ", 1, 1), ("2〜7個", 2, 7), ("8〜20個", 8, 20), ("21個以上", 21, None)]


def main() -> None:
    """日本語の見出し語を持つ概念ごとに、所属する兄弟グループの大きさを数える。"""
    with closing(sqlite3.connect(ROOT / "data/build/s7dict.sqlite")) as dictionary:
        sizes = [
            size
            for (size,) in dictionary.execute(
                "SELECT COUNT(*) OVER (PARTITION BY sibling_group_id) FROM synset"
                " WHERE sibling_group_id IS NOT NULL"
            )
        ]
        with_lemma = dictionary.execute(
            "SELECT COUNT(*) FROM synset WHERE representative_lemma_id IS NOT NULL"
        ).fetchone()[0]
        groups = dictionary.execute("SELECT COUNT(*) FROM sibling_group").fetchone()[0]
    with closing(sqlite3.connect(ROOT / "data/source/wnjpn.db")) as wordnet:
        multi_parent = wordnet.execute(
            "SELECT COUNT(*) FROM (SELECT synset1 FROM synlink"
            " WHERE link IN ('hype', 'inst') AND synset1 LIKE '%-n'"
            " GROUP BY synset1 HAVING COUNT(DISTINCT synset2) > 1)"
        ).fetchone()[0]

    print(f"日本語の見出し語を持つ概念: {with_lemma}")
    print(f"兄弟グループ: {groups}(所属する概念 {len(sizes)})")
    print(f"兄弟グループに入らない概念(上位語が無い): {with_lemma - len(sizes)}")
    for label, low, high in BUCKETS:
        count = sum(1 for size in sizes if size >= low and (high is None or size <= high))
        print(f"  {label}: {count}({count / len(sizes):.0%})")
    print(f"上位語が複数ある概念: {multi_parent}")


if __name__ == "__main__":
    main()
