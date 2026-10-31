"""POST /api/v1/transform のリクエストとレスポンス(機能設計書「変換リクエストとレスポンス」)。"""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from s7.api.schemas.base import CamelModel
from s7.domain import limits
from s7.domain.dictionary import ParentRelation
from s7.domain.transform import Mode, NounStatus

NounIndexKey = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]*)$")]
SynsetId = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}-n$")]


class TransformRequest(CamelModel):
    """変換のリクエスト。型の自動変換はしない(機能設計書「入力の型の厳しさ」)。"""

    # 型を変換しない。知らない項目は無視する(APIの互換性)
    model_config = ConfigDict(strict=True, extra="ignore")

    text: str = Field(max_length=limits.MAX_CHARS, description="1〜50,000文字(コードポイント数)")
    mode: Mode = Field(description="gojuon = 五十音順S+N、concept = 概念版S+N")
    n: int = Field(default=limits.DEFAULT_N, ge=limits.N_MIN, le=limits.N_MAX)
    exclusions: list[Annotated[int, Field(ge=0)]] = Field(
        default_factory=list,
        max_length=limits.MAX_EXCLUSIONS,
        description="[P1: F7] 置き換えない名詞の nounIndex",
    )
    sense_overrides: dict[NounIndexKey, SynsetId] = Field(
        default_factory=dict,
        max_length=limits.MAX_SENSE_OVERRIDES,
        description="[P1: F8] nounIndex(10進の文字列) → 使う概念ID",
    )

    @field_validator("text")
    @classmethod
    def _check_text(cls, text: str) -> str:
        # メッセージに本文を入れない(docs/development-guidelines.md「入力文を残さない」)
        if text == "" or text.isspace():
            raise PydanticCustomError("text_empty", "text is empty")
        if any(0xD800 <= ord(c) <= 0xDFFF for c in text):  # noqa: PLR2004  サロゲートの範囲
            raise PydanticCustomError("lone_surrogate", "text has a lone surrogate")
        return text


class ConceptRefSchema(CamelModel):
    """置換経路に表示する概念。"""

    synset_id: str
    lemma: str | None
    definition: str | None


class ConceptStepSchema(CamelModel):
    """階層を1段上がった記録。"""

    from_: ConceptRefSchema = Field(serialization_alias="from")
    to: ConceptRefSchema
    relation: ParentRelation


class GojuonRouteSchema(CamelModel):
    """五十音順S+Nの置換経路([P1: F6])。"""

    type: Literal["gojuon"] = "gojuon"
    from_index: int
    to_index: int
    wrapped: bool
    neighbors: list[str]
    neighbors_omitted: int


class ConceptRouteSchema(CamelModel):
    """概念版S+Nの置換経路([P1: F6])。"""

    type: Literal["concept"] = "concept"
    climbs: list[ConceptStepSchema]
    parent: ConceptRefSchema
    from_: ConceptRefSchema = Field(serialization_alias="from")
    to: ConceptRefSchema
    group_size: int
    wrapped: bool


# 応答は response_model_exclude_unset=True で返す(NounSegment の lemma などを、値があるときだけ
# 出すため)。そのため、既定値のある項目(type など)も作るときに必ず明示して渡す


class TextSegment(CamelModel):
    """名詞以外の文字列。空文字にはならない。"""

    type: Literal["text"] = "text"
    text: str


class NounSegment(CamelModel):
    """置換対象の名詞。lemma・synsetId・route は値があるときだけ入る。"""

    type: Literal["noun"] = "noun"
    noun_index: int
    original: str
    replaced: str
    status: NounStatus
    lemma: str | None = None
    synset_id: str | None = None
    route: Annotated[GojuonRouteSchema | ConceptRouteSchema, Field(discriminator="type")] | None = (
        None
    )


class TransformMeta(CamelModel):
    """変換の集計。"""

    mode: Mode
    n: int
    noun_count: int
    excluded_count: int
    replaced_count: int
    ignored_exclusions: list[int]
    ignored_sense_overrides: list[int]
    dictionary_version: str
    attribution: str


class TransformResponse(CamelModel):
    """変換のレスポンス。segments を順に連結すると元の文章になる。"""

    text: str
    segments: list[Annotated[TextSegment | NounSegment, Field(discriminator="type")]]
    meta: TransformMeta
