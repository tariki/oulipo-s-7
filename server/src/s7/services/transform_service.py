"""変換全体の流れをまとめる(TransformService)。

機能設計書「6. 変換の組み立て」の実装。
"""

import threading
from collections.abc import Mapping, Set
from dataclasses import dataclass, replace
from typing import Final

from s7.domain.transform import Mode, Noun, NounResult, TransformResult, TransformResultMeta
from s7.services.concept_shifter import ConceptShifter
from s7.services.gojuon_shifter import GojuonShifter
from s7.services.noun_extractor import NounExtractor

# 1プロセスで同時に動かす変換の数(architecture.md「同期処理と非同期処理」)
DEFAULT_MAX_CONCURRENCY: Final = 2


@dataclass(frozen=True, slots=True)
class _Request:
    """名詞ごとに変わらない変換の指定。"""

    mode: Mode
    n: int


@dataclass(frozen=True, slots=True)
class _Resolved:
    """名詞1つの結果と、語義の指定を使わなかったか。"""

    result: NounResult
    is_override_ignored: bool


class TransformService:
    """文章を変換する。"""

    def __init__(
        self,
        extractor: NounExtractor,
        gojuon: GojuonShifter,
        concept: ConceptShifter,
        dictionary_version: str,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        """変換に使う部品を受け取る。

        Args:
            extractor: 名詞の抽出。
            gojuon: 五十音順S+N。
            concept: 概念版S+N。
            dictionary_version: 変換用辞書のバージョン(結果の meta に入れる)。
            max_concurrency: 同時に動かす変換の数(1以上)。超えた分は順番に待つ。

        Raises:
            ValueError: max_concurrency が1未満のとき(0だとすべての変換が待ち続けるため)。
        """
        if max_concurrency < 1:
            raise ValueError("max_concurrency は1以上にしてください")
        self._extractor = extractor
        self._gojuon = gojuon
        self._concept = concept
        self._dictionary_version = dictionary_version
        # ルーターは同期関数でスレッドプールから呼ばれるため、スレッドのセマフォで数を抑える
        self._slots = threading.BoundedSemaphore(max_concurrency)

    def transform(
        self,
        text: str,
        mode: Mode,
        n: int,
        exclusions: Set[int] = frozenset(),
        sense_overrides: Mapping[int, str] | None = None,
    ) -> TransformResult:
        """文章中の名詞を、モードに応じてN個先の語に置き換える。

        Args:
            text: 文章。
            mode: gojuon(五十音順S+N)または concept(概念版S+N)。
            n: いくつ先に進むか(1〜99)。
            exclusions: 置き換えない名詞の nounIndex(F7)。
            sense_overrides: nounIndex → 使う語義の概念ID(F8)。概念版でだけ使う。

        Returns:
            変換の結果。今の文章に合わない除外や語義の指定は使わず、meta で知らせる。
        """
        with self._slots:
            return self._transform(text, mode, n, exclusions, sense_overrides or {})

    def _transform(
        self, text: str, mode: Mode, n: int, exclusions: Set[int], overrides: Mapping[int, str]
    ) -> TransformResult:
        request = _Request(mode=mode, n=n)
        segments: list[str | NounResult] = []
        ignored_overrides: list[int] = []
        noun_count = 0
        for raw in self._extractor.extract(text):
            if isinstance(raw, str):
                segments.append(raw)
                continue
            index = noun_count
            noun_count += 1
            override = overrides.get(index) if mode == "concept" else None
            resolved = self._resolve(index, raw, request, override, is_excluded=index in exclusions)
            segments.append(resolved.result)
            if resolved.is_override_ignored:
                ignored_overrides.append(index)
        if mode == "concept":
            ignored_overrides += [i for i in overrides if not 0 <= i < noun_count]
        results = [s for s in segments if isinstance(s, NounResult)]
        meta = TransformResultMeta(
            mode=mode,
            n=n,
            noun_count=noun_count,
            excluded_count=sum(r.status == "excluded" for r in results),
            replaced_count=sum(r.status in ("replaced", "climbed") for r in results),
            ignored_exclusions=tuple(sorted(e for e in exclusions if not 0 <= e < noun_count)),
            ignored_sense_overrides=tuple(sorted(ignored_overrides)),
            dictionary_version=self._dictionary_version,
        )
        return TransformResult(segments=tuple(segments), meta=meta)

    def _resolve(
        self, index: int, noun: Noun, request: _Request, override: str | None, *, is_excluded: bool
    ) -> _Resolved:
        """名詞の状態を決める(機能設計書「手順」3の表を上から順に判定する)。"""
        base = NounResult(index, noun.surface, noun.surface, "excluded", noun.lemma, None, None)
        lemma = noun.lemma
        if is_excluded:
            # 除外を外したときの語義を画面が示せるよう、見出し語と語義は入れる
            synset_id = None
            if lemma is not None and request.mode == "concept":
                synset_id = self._concept.select_sense(lemma.id, override).synset_id
            return _Resolved(replace(base, synset_id=synset_id), is_override_ignored=False)
        if lemma is None:
            not_found = replace(base, status="not_in_dictionary")
            return _Resolved(not_found, is_override_ignored=override is not None)
        if request.mode == "gojuon":
            return _Resolved(self._shift_gojuon(base, lemma.id, request.n), False)
        return self._shift_concept(base, lemma.id, request.n, override)

    def _shift_gojuon(self, base: NounResult, lemma_id: int, n: int) -> NounResult:
        shift = self._gojuon.shift(lemma_id, n)
        if shift is None:
            return replace(base, status="no_reading")
        return replace(base, replaced=shift.to_lemma.surface, status="replaced", route=shift.route)

    def _shift_concept(
        self, base: NounResult, lemma_id: int, n: int, override: str | None
    ) -> _Resolved:
        concept = self._concept.shift(lemma_id, n, override)
        is_ignored = override is not None and not concept.sense.is_override_applied
        result = replace(base, status="no_sibling", synset_id=concept.sense.synset_id)
        if concept.shift is not None:
            result = replace(
                result,
                replaced=concept.shift.to_lemma.surface,
                status="climbed" if concept.shift.route.climbs else "replaced",
                route=concept.shift.route,
            )
        return _Resolved(result, is_override_ignored=is_ignored)
