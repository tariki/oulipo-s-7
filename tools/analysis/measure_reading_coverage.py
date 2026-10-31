"""見出し語の読みの付与率を測る(docs/architecture.md「設計前の検証結果」の「読みの付与率」)。

日本語WordNetの名詞の見出し語すべて(除外リストを適用する前)について、機能設計書
「5. 見出し語の読みの決定」の手順で読みが決まるかを数え、決まらなかった理由の内訳を出す。

    uv run --directory server python ../tools/analysis/measure_reading_coverage.py
"""

import re
from collections import Counter
from pathlib import Path

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.domain.text import Morpheme
from s7builder.reading_assigner import ReadingAssigner
from s7builder.wordnet_reader import read_wordnet

ROOT = Path(__file__).resolve().parents[2]
VALID_READING = re.compile(r"[ぁ-ゖァ-ヶー・]+")
SYMBOL_POS = ("空白", "補助記号")


def main() -> None:
    """見出し語ごとに読みを決め、決め方と、決まらなかった理由を数える。"""
    surfaces = list(read_wordnet(ROOT / "data/source/wnjpn.db").lemma_synsets)
    tokenizer = SudachiTokenizer()
    assigner = ReadingAssigner(tokenizer)
    sources: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    sudachi_only = 0
    symbol_readings: list[str] = []
    for surface in surfaces:
        reading = assigner.assign(surface)
        sources[reading.source if reading else "none"] += 1
        morphemes = tokenizer.tokenize(surface, "C")
        joined = "".join(m.reading_form for m in morphemes)
        is_valid = not any(m.is_oov for m in morphemes) and bool(VALID_READING.fullmatch(joined))
        sudachi_only += is_valid
        symbols = [m for m in morphemes if m.pos[0] in SYMBOL_POS and m.surface not in "・･"]
        if reading and reading.source == "sudachi" and symbols:
            symbol_readings.append(f"{surface} → {reading.reading}")
        if reading is None:
            reasons[_reason(morphemes, joined)] += 1

    total = len(surfaces)
    print(f"見出し語: {total}")
    print(f"Sudachiの読みだけで決まる: {sudachi_only}({sudachi_only / total:.1%})")
    for source in ("kana", "sudachi", "none"):
        print(f"  {source}: {sources[source]}({sources[source] / total:.1%})")
    decided = total - sources["none"]
    print(f"読みが決まる(かなだけの表記を加えた付与率): {decided}({decided / total:.1%})")
    print("読みが決まらない理由:")
    for reason, count in reasons.most_common():
        print(f"  {reason}: {count}")
    print(f"空白・記号(中黒を除く)を含み、Sudachiの読みで決まった語: {len(symbol_readings)}")
    for line in symbol_readings[:20]:
        print(f"  {line}")


def _reason(morphemes: list[Morpheme], joined: str) -> str:
    if any(m.is_oov for m in morphemes):
        return "未知語を含む"
    if any(m.pos[0] in SYMBOL_POS and m.reading_form == "キゴウ" for m in morphemes):
        return "記号・空白の仮の読み(キゴウ)を含む"
    if not joined.replace("・", ""):
        return "読みが空"
    return "読みにかな以外が混ざる"


if __name__ == "__main__":
    main()
