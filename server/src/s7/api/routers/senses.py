"""GET /api/v1/senses(SenseRouter、[P1: F8])。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from s7.api.dependencies import Services, get_services
from s7.api.schemas.errors import ErrorResponse
from s7.api.schemas.senses import SenseItemSchema, SenseListResponse
from s7.domain import limits

router = APIRouter()


@router.get(
    "/api/v1/senses",
    response_model=SenseListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "lemma が無い、空、または100文字を超える"},
        404: {"model": ErrorResponse, "description": "見出し語が辞書に無い"},
    },
    summary="見出し語が持つ語義の一覧",
)
def list_senses(
    lemma: Annotated[
        str,
        Query(
            min_length=1,
            max_length=limits.MAX_LEMMA_CHARS,
            description="NounSegment.lemma の値(表記の完全一致で引く)",
        ),
    ],
    services: Annotated[Services, Depends(get_services)],
) -> SenseListResponse:
    """見出し語の語義を、順位の順に、定義文とその概念の見出し語つきで返す。"""
    result = services.senses.list_senses(lemma)
    return SenseListResponse(
        lemma=result.lemma,
        senses=[
            SenseItemSchema(
                synset_id=s.synset_id, rank=s.rank, definition=s.definition, lemmas=list(s.lemmas)
            )
            for s in result.senses
        ],
    )
