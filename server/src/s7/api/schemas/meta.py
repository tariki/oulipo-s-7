"""GET /api/v1/meta のレスポンス。"""

from s7.api.schemas.base import CamelModel


class LimitsSchema(CamelModel):
    """入力の上限と利用制限の値。"""

    max_chars: int
    n_min: int
    n_max: int
    max_exclusions: int
    max_sense_overrides: int
    transform_requests_per_minute: int
    auxiliary_requests_per_minute: int
    chars_per_minute: int


class MetaResponse(CamelModel):
    """辞書のバージョン、上限、出典。"""

    dictionary_version: str
    limits: LimitsSchema
    attribution: str
