"""辞書のメタ情報、入力の上限、利用制限、出典をまとめる(MetaService)。"""

from typing import Final

from s7.domain import limits
from s7.domain.transform import Limits, MetaInfo

# 出典の短い表記とライセンス全文の場所(docs/architecture.md「ライセンスとクレジット」)。
# APIの応答(meta.attribution)と GET /api/v1/meta で返す
ATTRIBUTION: Final = (
    "日本語WordNet 1.1(© 2009-2011 NICT、© 2012-2020 Francis Bond ほか)、"
    "SudachiDict(© Works Applications Co., Ltd.、Apache License 2.0)を使用しています。"
    "ライセンス全文: /about#credits"
)

LIMITS: Final = Limits(
    max_chars=limits.MAX_CHARS,
    n_min=limits.N_MIN,
    n_max=limits.N_MAX,
    max_exclusions=limits.MAX_EXCLUSIONS,
    max_sense_overrides=limits.MAX_SENSE_OVERRIDES,
    transform_requests_per_minute=limits.TRANSFORM_REQUESTS_PER_MINUTE,
    auxiliary_requests_per_minute=limits.AUXILIARY_REQUESTS_PER_MINUTE,
    chars_per_minute=limits.CHARS_PER_MINUTE,
)


class MetaService:
    """メタ情報。"""

    def __init__(self, dictionary_version: str) -> None:
        """変換用辞書のバージョンを受け取る。"""
        self._dictionary_version = dictionary_version

    def meta(self) -> MetaInfo:
        """辞書のバージョン、上限、出典を返す。"""
        return MetaInfo(
            dictionary_version=self._dictionary_version, limits=LIMITS, attribution=ATTRIBUTION
        )
