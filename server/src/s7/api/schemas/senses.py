"""GET /api/v1/senses のレスポンス([P1: F8])。"""

from s7.api.schemas.base import CamelModel


class SenseItemSchema(CamelModel):
    """語義の1件。"""

    synset_id: str
    rank: int
    definition: str | None
    lemmas: list[str]


class SenseListResponse(CamelModel):
    """見出し語の語義の一覧(rank の順)。"""

    lemma: str
    senses: list[SenseItemSchema]
