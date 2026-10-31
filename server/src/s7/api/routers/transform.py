"""POST /api/v1/transform(TransformRouter)。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from s7.api.dependencies import Services, get_services
from s7.api.schemas.errors import ErrorResponse
from s7.api.schemas.transform import (
    ConceptRefSchema,
    ConceptRouteSchema,
    ConceptStepSchema,
    GojuonRouteSchema,
    NounSegment,
    TextSegment,
    TransformMeta,
    TransformRequest,
    TransformResponse,
)
from s7.domain.transform import ConceptRef, ConceptRoute, GojuonRoute, NounResult, TransformResult

router = APIRouter()

_ERRORS = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in [
        (400, "入力の不備"),
        (413, "本文が1MBを超える"),
        (429, "利用制限を超えた(Retry-After の秒数後に再試行する)"),
        (500, "想定外のエラー"),
        (503, "起動中(Retry-After の秒数後に再試行する)"),
    ]
}


@router.post(
    "/api/v1/transform",
    response_model=TransformResponse,
    response_model_exclude_unset=True,
    responses=_ERRORS,  # type: ignore[arg-type]
    summary="文章中の名詞を、辞書のN個先の語に置き換える",
)
def transform(
    body: TransformRequest,
    request: Request,
    services: Annotated[Services, Depends(get_services)],
) -> TransformResponse:
    """文章を変換する。CPUを使うため同期関数にする(FastAPIがスレッドプールで動かす)。"""
    # リクエストのログには文字数だけを出す(本文は出さない)
    request.state.transform_log = {"mode": body.mode, "n": body.n, "chars": len(body.text)}
    result = services.transform.transform(
        body.text,
        body.mode,
        body.n,
        exclusions=frozenset(body.exclusions),
        sense_overrides={int(k): v for k, v in body.sense_overrides.items()},
    )
    return _to_response(result, services.meta.meta().attribution)


def _to_response(result: TransformResult, attribution: str) -> TransformResponse:
    meta = result.meta
    return TransformResponse(
        text=result.text,
        segments=[
            TextSegment(type="text", text=s) if isinstance(s, str) else _to_noun_segment(s)
            for s in result.segments
        ],
        meta=TransformMeta(
            mode=meta.mode,
            n=meta.n,
            noun_count=meta.noun_count,
            excluded_count=meta.excluded_count,
            replaced_count=meta.replaced_count,
            ignored_exclusions=list(meta.ignored_exclusions),
            ignored_sense_overrides=list(meta.ignored_sense_overrides),
            dictionary_version=meta.dictionary_version,
            attribution=attribution,
        ),
    )


def _to_noun_segment(noun: NounResult) -> NounSegment:
    """値のある項目だけを渡す(渡さなかった項目は応答に出さない。response_model_exclude_unset)。"""
    optional: dict[str, object] = {}
    if noun.lemma is not None:
        optional["lemma"] = noun.lemma.surface
    if noun.synset_id is not None:
        optional["synset_id"] = noun.synset_id
    if isinstance(noun.route, GojuonRoute):
        optional["route"] = GojuonRouteSchema(
            type="gojuon",
            from_index=noun.route.from_index,
            to_index=noun.route.to_index,
            wrapped=noun.route.wrapped,
            neighbors=list(noun.route.neighbors),
            neighbors_omitted=noun.route.neighbors_omitted,
        )
    elif isinstance(noun.route, ConceptRoute):
        optional["route"] = _to_concept_route(noun.route)
    return NounSegment(
        type="noun",
        noun_index=noun.noun_index,
        original=noun.original,
        replaced=noun.replaced,
        status=noun.status,
        **optional,  # type: ignore[arg-type]
    )


def _to_concept_route(route: ConceptRoute) -> ConceptRouteSchema:
    return ConceptRouteSchema(
        type="concept",
        climbs=[
            ConceptStepSchema(from_=_ref(s.from_), to=_ref(s.to), relation=s.relation)
            for s in route.climbs
        ],
        parent=_ref(route.parent),
        from_=_ref(route.from_),
        to=_ref(route.to),
        group_size=route.group_size,
        wrapped=route.wrapped,
    )


def _ref(ref: ConceptRef) -> ConceptRefSchema:
    # lemma・definition は null でも必ず出す(exclude_unset で消えないよう明示して渡す)
    return ConceptRefSchema(synset_id=ref.synset_id, lemma=ref.lemma, definition=ref.definition)
