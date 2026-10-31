"""環境変数から読む実行時の設定。

一覧と既定値は docs/architecture.md「環境変数」。利用制限の値は設定にせずコードで持つ。
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from s7.logging_config import LogFormat, Severity

# server/src/s7/config.py から4段上がリポジトリ直下。
# 既定のパスをここから解決し、どのディレクトリから起動しても同じファイルを指すようにする。
# ソースを置いたまま動かす前提(手元とテスト)。コンテナなどインストールして動かす場合は、
# S7_DICTIONARY_PATH・S7_STATIC_DIR を必ず絶対パスで指定する(Dockerfile の ENV)
REPO_ROOT: Final = Path(__file__).resolve().parents[3]

DEFAULT_PORT: Final = 8000
DEFAULT_DICTIONARY_PATH: Final = "data/build/s7dict.sqlite"
DEFAULT_STATIC_DIR: Final = "web/dist"
MAX_PORT: Final = 65535

# 文字列から Literal の型に絞るための対応表
_LOG_FORMATS: Final[Mapping[str, LogFormat]] = {"json": "json", "text": "text"}
_LOG_LEVELS: Final[Mapping[str, Severity]] = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
}


@dataclass(frozen=True, slots=True)
class Settings:
    """実行時の設定。

    Attributes:
        port: 待ち受けるポート。Uvicorn の起動時に --port で渡す(アプリはこの値で待ち受けない)。
        dictionary_path: 変換用辞書のパス(絶対パス)。
        static_dir: 画面のビルド結果のディレクトリ(絶対パス)。
        log_format: ログの形式。
        log_level: ログの出力レベル。
        trusted_proxy_hops: 信頼する前段のプロキシの段数。
    """

    port: int
    dictionary_path: Path
    static_dir: Path
    log_format: LogFormat
    log_level: Severity
    trusted_proxy_hops: int


def load_settings(environ: Mapping[str, str]) -> Settings:
    """環境変数から設定を作る。

    値の前後の空白は取り除く。空の値は、設定していないものとして既定値を使う
    (コンテナの設定では空で渡されることがあるため)。

    Args:
        environ: 環境変数(通常は os.environ)。

    Returns:
        設定。相対パスはリポジトリ直下を基準に絶対パスにしたもの。

    Raises:
        ValueError: 値が不正なとき。メッセージには環境変数の名前だけを入れる。
    """
    return Settings(
        port=_read_int(environ, "PORT", DEFAULT_PORT, minimum=1, maximum=MAX_PORT),
        dictionary_path=_read_path(environ, "S7_DICTIONARY_PATH", DEFAULT_DICTIONARY_PATH),
        static_dir=_read_path(environ, "S7_STATIC_DIR", DEFAULT_STATIC_DIR),
        log_format=_read_choice(environ, "S7_LOG_FORMAT", "json", _LOG_FORMATS, str.lower),
        log_level=_read_choice(environ, "S7_LOG_LEVEL", "INFO", _LOG_LEVELS, str.upper),
        trusted_proxy_hops=_read_int(environ, "S7_TRUSTED_PROXY_HOPS", 0, minimum=0),
    )


def _read_raw(environ: Mapping[str, str], name: str) -> str | None:
    raw = environ.get(name, "").strip()
    return raw or None


def _read_int(
    environ: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    raw = _read_raw(environ, name)
    if raw is None:
        return default
    # int() は "1_000" や全角数字も受け付けるため、ASCIIの数字だけに絞る
    if not (raw.isascii() and raw.isdigit()):
        raise ValueError(f"{name} は0以上の整数で指定してください")
    value = int(raw)
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} が範囲外です")
    return value


def _read_path(environ: Mapping[str, str], name: str, default: str) -> Path:
    path = Path(_read_raw(environ, name) or default)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_choice[T](
    environ: Mapping[str, str],
    name: str,
    default: str,
    choices: Mapping[str, T],
    normalize: Callable[[str], str],
) -> T:
    choice = choices.get(normalize(_read_raw(environ, name) or default))
    if choice is None:
        raise ValueError(f"{name} は {'、'.join(choices)} のどれかで指定してください")
    return choice
