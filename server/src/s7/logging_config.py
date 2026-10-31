"""構造化ログの設定と、ログを出す関数。

ログの形式は docs/functional-design.md「ログの形式」。標準出力に1行1つのJSONで出す。
`logging` を直接使ってよいのはこのモジュールだけ(ほかはここの関数を使う)。
入力文と変換結果は、どの関数にも渡さない(docs/development-guidelines.md「入力文を残さない」)。
"""

import json
import logging
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Final, Literal

Kind = Literal["request", "analytics", "app"]
Severity = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["json", "text"]
FieldValue = str | int | float | bool | None

_LOGGER: Final = logging.getLogger("s7")
_KIND_ATTR: Final = "s7_kind"
_FIELDS_ATTR: Final = "s7_fields"
_SEVERITY_LEVELS: Final[Mapping[Severity, int]] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}
# Uvicornのアクセスログはクエリ文字列(見出し語)をそのまま出すため止める。
# リクエストのログは RequestLogging ミドルウェアが出す
_UVICORN_LOGGERS: Final = ("uvicorn", "uvicorn.error")
_UVICORN_ACCESS_LOGGER: Final = "uvicorn.access"


def configure_logging(log_format: LogFormat, log_level: Severity) -> None:
    """ルートのロガーに標準出力のハンドラーを1つだけ付け、Uvicornのログもそこへ流す。

    Args:
        log_format: json(1行1つのJSON)か text(手元で読みやすい形式)。
        log_level: 出力する最低の重要度。
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if log_format == "json" else TextFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(_SEVERITY_LEVELS[log_level])

    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    access_logger = logging.getLogger(_UVICORN_ACCESS_LOGGER)
    access_logger.handlers = []
    access_logger.propagate = False
    access_logger.disabled = True


def log_app(message: str, *, severity: Severity = "INFO", **fields: FieldValue) -> None:
    """`kind = app` の行を出す(起動、辞書の読み込み完了など)。

    Args:
        message: 人が読む説明。本文や見出し語を含めない。
        severity: 重要度。
        **fields: 追加の項目。名前はsnake_caseで渡し、ログではcamelCaseになる。
            必須の項目(time・severity・kind)と同じ名前は無視する。
    """
    _emit("app", severity, message, fields)


def _emit(kind: Kind, severity: Severity, message: str, fields: Mapping[str, FieldValue]) -> None:
    _LOGGER.log(
        _SEVERITY_LEVELS[severity],
        message,
        extra={_KIND_ATTR: kind, _FIELDS_ATTR: {_to_camel(k): v for k, v in fields.items()}},
    )


class JsonFormatter(logging.Formatter):
    """1行1つのJSONにする。必須の項目は time・severity・kind・message。"""

    def format(self, record: logging.LogRecord) -> str:
        """ログの1件をJSONの1行にする。"""
        return json.dumps(_to_entry(record), ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """手元で読むための1行の形式(`time severity kind message key=value ...`)。"""

    def format(self, record: logging.LogRecord) -> str:
        """ログの1件を読みやすい1行にする。"""
        entry = _to_entry(record)
        head = f"{entry.pop('time')} {entry.pop('severity')} {entry.pop('kind')} "
        # 外部ライブラリのメッセージに改行が入っても1行に保つ
        head += str(entry.pop("message")).replace("\n", "\\n")
        pairs = [f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in entry.items()]
        return " ".join([head, *pairs])


def _to_entry(record: logging.LogRecord) -> dict[str, object]:
    # 追加の項目を先に入れ、必須の項目で上書きする(追加の項目で kind などを変えられないように)
    entry: dict[str, object] = dict(getattr(record, _FIELDS_ATTR, {}))
    entry.update(
        time=_format_time(record.created),
        severity=_severity_of(record.levelno),
        kind=getattr(record, _KIND_ATTR, "app"),
        message=record.getMessage(),
    )
    if record.exc_info is not None and record.exc_info[0] is not None:
        # 例外のメッセージには入力値が入りうるため、型と場所だけを出す
        exc_type, _, exc_traceback = record.exc_info
        entry["exceptionType"] = exc_type.__name__
        entry["stack"] = _format_stack(exc_traceback)
    return entry


def _format_time(created: float) -> str:
    stamp = datetime.fromtimestamp(created, tz=UTC).isoformat(timespec="milliseconds")
    return stamp.replace("+00:00", "Z")


def _severity_of(levelno: int) -> Severity:
    if levelno >= logging.ERROR:
        return "ERROR"
    if levelno >= logging.WARNING:
        return "WARNING"
    if levelno >= logging.INFO:
        return "INFO"
    return "DEBUG"


def _format_stack(tb: TracebackType | None) -> list[str]:
    # サーバーのディレクトリ構成を出さないため、ファイル名だけにする
    return [
        f"{Path(frame.filename).name}:{frame.lineno} {frame.name}"
        for frame in traceback.extract_tb(tb)
    ]


def _to_camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)
