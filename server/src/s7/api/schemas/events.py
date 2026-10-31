"""POST /api/v1/events のリクエスト(機能設計書「アクセス解析(匿名)」)。

受け付けるイベントと項目は決まったものだけ。知らない項目は捨てる(ログにも出さない)。
"""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints

from s7.api.schemas.base import CamelModel
from s7.domain import limits
from s7.domain.errors import ErrorCode
from s7.domain.transform import Mode

PageViewId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16}$")]
Count = Annotated[int, Field(ge=0)]


class _Event(CamelModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    page_view_id: PageViewId


class PageViewEvent(_Event):
    """変換画面を開いた。"""

    event: Literal["page_view"]


class TransformEvent(_Event):
    """利用者の1回の変換の操作が終わった(成功・失敗とも)。"""

    event: Literal["transform"]
    transform_seq: Annotated[int, Field(ge=1)]
    mode: Mode
    n: Annotated[int, Field(ge=limits.N_MIN, le=limits.N_MAX)]
    chars_bucket: Literal["le1000", "le10000", "le50000"]
    success: bool
    noun_count: Count | None = None
    excluded_count: Count | None = None
    replaced_count: Count | None = None
    error_code: ErrorCode | Literal["NETWORK_ERROR"] | None = None


class CopyEvent(_Event):
    """結果をコピーした。"""

    event: Literal["copy"]
    transform_seq: Annotated[int, Field(ge=1)]


AnalyticsEvent = Annotated[PageViewEvent | TransformEvent | CopyEvent, Field(discriminator="event")]
