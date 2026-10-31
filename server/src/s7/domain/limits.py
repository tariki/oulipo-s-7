"""入力の上限と利用制限の値。

API仕様の一部(GET /api/v1/meta で公開する)のため、環境変数ではなくコードで持つ
(docs/architecture.md「環境変数」)。APIのスキーマ、MetaService、RateLimiter が共有する。
"""

from typing import Final

MAX_CHARS: Final = 50_000
DEFAULT_N: Final = 7
N_MIN: Final = 1
N_MAX: Final = 99
MAX_EXCLUSIONS: Final = 1_000
MAX_SENSE_OVERRIDES: Final = 1_000
# 語義の一覧(F8)で受け付ける見出し語の長さ
MAX_LEMMA_CHARS: Final = 100
# 本文の最大サイズ。50,000文字をすべて \uXXXX で書いた場合(最大600,000バイト)も受け付ける
MAX_BODY_BYTES: Final = 1_048_576

TRANSFORM_REQUESTS_PER_MINUTE: Final = 30
AUXILIARY_REQUESTS_PER_MINUTE: Final = 120
CHARS_PER_MINUTE: Final = 200_000
