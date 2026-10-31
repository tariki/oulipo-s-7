"""辞書ビルダーのコマンド。

    uv run --directory server python -m s7builder build

パスを省くと、リポジトリ直下を基準にした既定のパスを使う。
"""

import argparse
import sqlite3
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Final

from s7.adapters.sudachi_tokenizer import SudachiTokenizer
from s7.adapters.tokenizer import Tokenizer
from s7.logging_config import configure_logging, log_app
from s7builder.build_report import write_build_report
from s7builder.dictionary_builder import DictionaryBuilder
from s7builder.errors import BuildError

# server/src/s7builder/__main__.py から4段上がリポジトリ直下(s7/config.py と同じ考え方。
# 辞書ビルダーは config.py を使わないため、ここで求める)
REPO_ROOT: Final = Path(__file__).resolve().parents[3]


def main(
    argv: Sequence[str] | None = None,
    tokenizer_factory: Callable[[], Tokenizer] = SudachiTokenizer,
) -> int:
    """コマンドを実行する。

    Args:
        argv: コマンドライン引数(省くと sys.argv)。
        tokenizer_factory: 読みの決定に使う Tokenizer を作る関数(テストで差し替える)。

    Returns:
        終了コード。失敗したら1。
    """
    args = _parse_args(argv)
    configure_logging("text", "INFO")
    try:
        _build(args, tokenizer_factory)
    # SQLiteやファイルの書き込みの失敗も、トレースバックではなく理由の1行で終える
    except (BuildError, sqlite3.Error, OSError) as error:
        sys.stderr.write(f"辞書のビルドに失敗しました: {error}\n")
        return 1
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m s7builder", description="変換用辞書を作る")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="日本語WordNetから変換用辞書とビルドの報告を作る")
    for name, default, help_text in [
        ("--wordnet", "data/source/wnjpn.db", "日本語WordNet 1.1"),
        ("--excluded", "data/excluded-lemmas.txt", "置換先から除外する語のリスト"),
        ("--license", "licenses/wordnet-ja.txt", "日本語WordNetのライセンス文"),
        ("--output", "data/build/s7dict.sqlite", "変換用辞書の出力先"),
        ("--report", "data/reports/build-report.json", "ビルドの報告の出力先"),
    ]:
        build.add_argument(name, type=_resolve, default=_resolve(default), help=help_text)
    return parser.parse_args(argv)


def _resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _build(args: argparse.Namespace, tokenizer_factory: Callable[[], Tokenizer]) -> None:
    license_path: Path = args.license
    if not license_path.is_file():
        raise BuildError(f"日本語WordNetのライセンス文がありません: {license_path}")
    log_app("辞書のビルドを始めます")
    builder = DictionaryBuilder(
        tokenizer=tokenizer_factory(),
        sudachidict_version=f"core-{version('sudachidict-core')}",
        wordnet_license=license_path.read_text(encoding="utf-8"),
    )
    report = builder.build(args.wordnet, args.excluded, args.output)
    write_build_report(report, args.report)
    log_app("辞書のビルドが終わりました", **asdict(report.meta))


if __name__ == "__main__":
    sys.exit(main())
