"""変換の中間の型と結果の型。

機能設計書「6. 変換の組み立て」と「変換リクエストとレスポンス(APIの型)」に対応する。
サービスどうしが型のためだけに互いを取り込まないよう、ここにまとめる。
"""

from dataclasses import dataclass
from typing import Literal

from s7.domain.dictionary import Lemma, ParentRelation
from s7.domain.text import Morpheme

Mode = Literal["gojuon", "concept"]
NounStatus = Literal[
    "replaced", "climbed", "not_in_dictionary", "no_reading", "no_sibling", "excluded"
]


@dataclass(frozen=True, slots=True)
class Noun:
    """文章から取り出した置換対象の名詞。

    Attributes:
        morphemes: 名詞を作る形態素(複合名詞なら複数)。
        lemma: 引き当てた見出し語。辞書に無ければNone。
    """

    morphemes: tuple[Morpheme, ...]
    lemma: Lemma | None

    @property
    def surface(self) -> str:
        """形態素の表記をつなげたもの(入力文のまま)。"""
        return "".join(m.surface for m in self.morphemes)


# 名詞以外の文字列、または名詞
RawSegment = str | Noun


@dataclass(frozen=True, slots=True)
class GojuonRoute:
    """五十音順S+Nの置換経路。

    Attributes:
        from_index: 元の語の五十音順リスト上の位置。
        to_index: 変換後の語の位置。
        wrapped: 末尾から先頭に戻ったか。
        neighbors: 間にある見出し語の表記(リストの並び順)。多いときは最初と最後の3語だけ。
        neighbors_omitted: neighbors から省いた語の数。
    """

    from_index: int
    to_index: int
    wrapped: bool
    neighbors: tuple[str, ...]
    neighbors_omitted: int


@dataclass(frozen=True, slots=True)
class ConceptRef:
    """置換経路に表示する概念。

    APIレイヤーは辞書を引けないため、代表語と定義文をここに詰めて渡す。

    Attributes:
        synset_id: 概念ID。
        lemma: 代表語の表記。日本語の見出し語が無い概念はNone。
        definition: 日本語の定義文。無ければ英語の定義文。
    """

    synset_id: str
    lemma: str | None
    definition: str | None


@dataclass(frozen=True, slots=True)
class ConceptStep:
    """階層を1段上がった記録。

    Attributes:
        from_: 上がる前の概念。
        to: 上がった先の概念(上位語)。
        relation: from_ から to への関係。
    """

    from_: ConceptRef
    to: ConceptRef
    relation: ParentRelation


@dataclass(frozen=True, slots=True)
class ConceptRoute:
    """概念版S+Nの置換経路。

    Attributes:
        climbs: 階層を上がった経路(上がっていなければ空)。
        parent: 兄弟グループの共通の上位語。
        from_: 元の概念(上がった場合は上がった先の概念)。
        to: 変換後の概念。
        group_size: 兄弟グループの大きさ。
        wrapped: 兄弟グループの末尾から先頭に戻ったか。
    """

    climbs: tuple[ConceptStep, ...]
    parent: ConceptRef
    from_: ConceptRef
    to: ConceptRef
    group_size: int
    wrapped: bool


@dataclass(frozen=True, slots=True)
class GojuonShift:
    """五十音順S+Nで置き換えた結果。"""

    to_lemma: Lemma
    route: GojuonRoute


@dataclass(frozen=True, slots=True)
class ConceptShift:
    """概念版S+Nで置き換えた結果。to_lemma は置換先の概念の代表語。"""

    to_lemma: Lemma
    route: ConceptRoute


@dataclass(frozen=True, slots=True)
class SenseChoice:
    """選んだ語義。

    Attributes:
        synset_id: 使う語義の概念ID。
        is_override_applied: 語義の上書き指定(F8)を使ったか。
    """

    synset_id: str
    is_override_applied: bool


@dataclass(frozen=True, slots=True)
class ConceptShiftResult:
    """ConceptShifter の結果。

    Attributes:
        sense: 元の語の語義。
        shift: 置き換えた結果。Noneなら最上位まで兄弟が無い(no_sibling)。
    """

    sense: SenseChoice
    shift: ConceptShift | None


@dataclass(frozen=True, slots=True)
class NounResult:
    """名詞1つの変換結果(APIの NounSegment)。

    Attributes:
        noun_index: 文章中の名詞の通し番号(0始まり)。
        original: 元の語(入力文のまま)。
        replaced: 変換後の語。置き換えなかった場合は original と同じ。
        status: 状態。
        lemma: 引き当てた見出し語。辞書に無ければNone。
        synset_id: 元の名詞に選ばれた語義。概念版で見出し語があるときだけ。
        route: 置換経路。replaced・climbed のときだけ。
    """

    noun_index: int
    original: str
    replaced: str
    status: NounStatus
    lemma: Lemma | None
    synset_id: str | None
    route: GojuonRoute | ConceptRoute | None


@dataclass(frozen=True, slots=True)
class TransformResultMeta:
    """変換の集計(APIの TransformMeta から attribution を除いたもの)。

    Attributes:
        mode: モード。
        n: いくつ先に進めたか。
        noun_count: 名詞の数(除外・辞書に無い語を含む)。
        excluded_count: excluded の数。
        replaced_count: replaced と climbed の数。
        ignored_exclusions: 使わなかった除外の指定(小さい順)。
        ignored_sense_overrides: 使わなかった語義の指定の nounIndex(小さい順)。
        dictionary_version: 変換用辞書のバージョン。
    """

    mode: Mode
    n: int
    noun_count: int
    excluded_count: int
    replaced_count: int
    ignored_exclusions: tuple[int, ...]
    ignored_sense_overrides: tuple[int, ...]
    dictionary_version: str


@dataclass(frozen=True, slots=True)
class TransformResult:
    """変換の結果。

    Attributes:
        segments: 元の文章を区切ったもの。名詞以外の文字列(空にならない)と名詞の結果。
        meta: 集計。
    """

    segments: tuple[str | NounResult, ...]
    meta: TransformResultMeta

    @property
    def text(self) -> str:
        """変換後の文章(文字列と各名詞の replaced を順につなげたもの)。"""
        return "".join(s if isinstance(s, str) else s.replaced for s in self.segments)


@dataclass(frozen=True, slots=True)
class SenseItem:
    """語義の一覧(F8)の1件。

    Attributes:
        synset_id: 概念ID。
        rank: 順位(0が既定で選ばれる語義)。
        definition: 日本語の定義文。無ければ英語の定義文。
        lemmas: その概念の日本語の見出し語(Lemma.id の順)。
    """

    synset_id: str
    rank: int
    definition: str | None
    lemmas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SenseList:
    """見出し語の語義の一覧(rank の順)。"""

    lemma: str
    senses: tuple[SenseItem, ...]


@dataclass(frozen=True, slots=True)
class Limits:
    """入力の上限と利用制限の値(GET /api/v1/meta)。"""

    max_chars: int
    n_min: int
    n_max: int
    max_exclusions: int
    max_sense_overrides: int
    transform_requests_per_minute: int
    auxiliary_requests_per_minute: int
    chars_per_minute: int


@dataclass(frozen=True, slots=True)
class MetaInfo:
    """辞書のメタ情報と上限、出典(GET /api/v1/meta)。"""

    dictionary_version: str
    limits: Limits
    attribution: str
