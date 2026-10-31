"""例外。

docs/development-guidelines.md「エラーハンドリング」。メッセージには本文や名詞を入れず、
数値・識別子だけを入れる。
"""

from typing import ClassVar, Literal

# 機能設計書「エラーコードの一覧」と同じ
ErrorCode = Literal[
    "TEXT_EMPTY",
    "TEXT_TOO_LONG",
    "INVALID_MODE",
    "INVALID_N",
    "INVALID_REQUEST",
    "LEMMA_NOT_FOUND",
    "PAYLOAD_TOO_LARGE",
    "RATE_LIMITED",
    "SERVICE_STARTING",
    "INTERNAL_ERROR",
]


class DomainError(Exception):
    """利用者に伝えるエラーの基底。code はAPIのエラーコード。"""

    code: ClassVar[ErrorCode]


class LemmaNotFoundError(DomainError):
    """語義の一覧(F8)で、指定の見出し語が辞書に無い。"""

    code = "LEMMA_NOT_FOUND"


class DictionaryIntegrityError(Exception):
    """変換用辞書の不備。読み込み時の検査で防ぐため、実行時に起きたら500にする。"""

    def __init__(self, identifier: str, kind: str = "概念") -> None:
        """不備のある識別子を受け取る。

        Args:
            identifier: 見つからなかったものの識別子(概念ID、見出し語の番号など)。
            kind: 識別子の種類(メッセージに使う)。
        """
        super().__init__(f"{kind} {identifier} が変換用辞書にありません")
        self.identifier = identifier


class RateLimitedError(DomainError):
    """利用制限を超えた。retry_after は再試行までの秒数(Retry-After に入れる)。"""

    code = "RATE_LIMITED"

    def __init__(self, retry_after: int) -> None:
        """再試行までの秒数を受け取る。"""
        super().__init__(f"retry after {retry_after}s")
        self.retry_after = retry_after
