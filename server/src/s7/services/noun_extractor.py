"""文章から置換対象の名詞を取り出す(NounExtractor)。

機能設計書「1. 名詞抽出と最長一致」の実装。
"""

import unicodedata
from collections.abc import Sequence
from typing import Final

from s7.adapters.tokenizer import Tokenizer
from s7.domain.dictionary import Lemma
from s7.domain.text import Morpheme
from s7.domain.transform import Noun, RawSegment
from s7.repositories.dictionary_repository import DictionaryRepository
from s7.services.formal_nouns import FORMAL_NOUNS
from s7.services.text_chunker import split_for_tokenizer

# 1回に連結を試す形態素の数の上限(1区間の計算量を「形態素数 × 8」に抑える)
MAX_MERGE_MORPHEMES: Final = 8


class NounExtractor:
    """文章を名詞とそれ以外の文字列に分ける。"""

    def __init__(self, tokenizer: Tokenizer, repo: DictionaryRepository) -> None:
        """形態素解析と、見出し語を引き当てる辞書を受け取る。

        Args:
            tokenizer: 形態素解析(モードAで使う)。
            repo: 変換用辞書。
        """
        self._tokenizer = tokenizer
        self._repo = repo

    def extract(self, text: str) -> list[RawSegment]:
        """文章を、名詞以外の文字列と名詞を交互に並べた列にする。

        Args:
            text: 文章。

        Returns:
            名詞以外の文字列(空にならない)と名詞の列。順につなげると text に戻る。
        """
        segments: list[RawSegment] = []
        for part in split_for_tokenizer(text):
            # 分けた位置をまたぐ候補区間は作らない(機能設計書「7. 長文の分割」)
            for item in self._extract_part(self._tokenizer.tokenize(part, "A")):
                _append(segments, item)
        return segments

    def _extract_part(self, morphemes: Sequence[Morpheme]) -> list[RawSegment]:
        result: list[RawSegment] = []
        run: list[Morpheme] = []
        for morpheme in morphemes:
            if _is_candidate(morpheme):
                run.append(morpheme)
                continue
            result.extend(self._merge_run(run))
            run = []
            result.append(morpheme.surface)
        result.extend(self._merge_run(run))
        return result

    def _merge_run(self, run: Sequence[Morpheme]) -> list[RawSegment]:
        """候補区間を名詞と文字列にする。名詞にならない形態素は文字列として残す。"""
        result: list[RawSegment] = []
        for item in merge_longest(run, self._repo):
            result.append(item if isinstance(item, Noun) else item.surface)
        return result


def merge_longest(run: Sequence[Morpheme], repo: DictionaryRepository) -> list[Noun | Morpheme]:
    """候補区間を、辞書との最長一致で名詞にまとめる。

    機能設計書「1. 名詞抽出と最長一致」ステップ3の実装。

    Args:
        run: 候補区間(普通名詞・固有名詞・数詞・接頭辞・名詞的接尾辞が連続する形態素)。
        repo: 連結した表記から見出し語を引き当てる辞書。

    Returns:
        名詞と、名詞にならなかった形態素の列(元の順)。1形態素の普通名詞は辞書に無くても名詞にする。
    """
    result: list[Noun | Morpheme] = []
    i = 0
    while i < len(run):
        matched = _match_compound(run, i, repo)
        if matched is None and _is_single_noun(run[i]):
            matched = Noun(morphemes=(run[i],), lemma=lookup(run[i : i + 1], repo))
        if matched is None:
            result.append(run[i])
            i += 1
        else:
            result.append(matched)
            i += len(matched.morphemes)
    return result


def lookup(part: Sequence[Morpheme], repo: DictionaryRepository) -> Lemma | None:
    """形態素の並びから見出し語を引き当てる(ステップ4)。

    表記 → 表記のNFKC → Sudachiの正規化表記(1形態素のときだけ)の順に探す。
    """
    surface = "".join(m.surface for m in part)
    candidates = [surface, unicodedata.normalize("NFKC", surface)]
    if len(part) == 1:
        candidates.append(part[0].normalized_form)
    for candidate in candidates:
        lemma = repo.find_lemma(candidate)
        if lemma is not None:
            return lemma
    return None


def _match_compound(run: Sequence[Morpheme], start: int, repo: DictionaryRepository) -> Noun | None:
    """位置 start から始まる2形態素以上の連結のうち、辞書にある最長のもの。"""
    for end in range(min(len(run), start + MAX_MERGE_MORPHEMES), start + 1, -1):
        part = run[start:end]
        if not any(_is_common_noun_or_suffix(m) for m in part):
            continue
        lemma = lookup(part, repo)
        if lemma is not None:
            return Noun(morphemes=tuple(part), lemma=lemma)
    return None


def _append(segments: list[RawSegment], item: RawSegment) -> None:
    """文字列が続くときは1つにつなげる。空の文字列は入れない。"""
    if isinstance(item, str):
        if not item:
            return
        if segments and isinstance(segments[-1], str):
            segments[-1] += item
            return
    segments.append(item)


def _is_common_noun(m: Morpheme) -> bool:
    return m.pos[:2] == ("名詞", "普通名詞")


def _is_common_noun_or_suffix(m: Morpheme) -> bool:
    return _is_common_noun(m) or m.pos[:2] == ("接尾辞", "名詞的")


def _is_single_noun(m: Morpheme) -> bool:
    """1形態素で名詞になるか(普通名詞で、形式名詞でない)。形式名詞は表記だけで判定する。"""
    return _is_common_noun(m) and m.surface not in FORMAL_NOUNS


def _is_candidate(m: Morpheme) -> bool:
    """候補区間に入る形態素か(機能設計書「1. 名詞抽出と最長一致」ステップ2の表)。"""
    return (
        _is_common_noun_or_suffix(m)
        or m.pos[:2] in {("名詞", "固有名詞"), ("名詞", "数詞")}
        or m.pos[0] == "接頭辞"
    )
