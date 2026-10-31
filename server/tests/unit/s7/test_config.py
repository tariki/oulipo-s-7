from pathlib import Path

import pytest

from s7.config import REPO_ROOT, load_settings


def test_repo_root_points_to_repository_root() -> None:
    # Then: リポジトリ直下には server/ と docs/ がある
    assert (REPO_ROOT / "server" / "pyproject.toml").is_file()
    assert (REPO_ROOT / "docs").is_dir()


def test_load_settings_without_env_uses_defaults() -> None:
    # When
    settings = load_settings({})

    # Then: docs/architecture.md「環境変数」の既定値
    assert settings.port == 8000
    assert settings.dictionary_path == REPO_ROOT / "data" / "build" / "s7dict.sqlite"
    assert settings.static_dir == REPO_ROOT / "web" / "dist"
    assert settings.log_format == "json"
    assert settings.log_level == "INFO"
    assert settings.trusted_proxy_hops == 0


def test_load_settings_reads_each_variable() -> None:
    # Given
    environ = {
        "PORT": "9000",
        "S7_DICTIONARY_PATH": "/opt/s7/s7dict.sqlite",
        "S7_STATIC_DIR": "/opt/s7/static",
        "S7_LOG_FORMAT": "text",
        "S7_LOG_LEVEL": "warning",
        "S7_TRUSTED_PROXY_HOPS": "1",
    }

    # When
    settings = load_settings(environ)

    # Then
    assert settings.port == 9000
    assert settings.dictionary_path == Path("/opt/s7/s7dict.sqlite")
    assert settings.static_dir == Path("/opt/s7/static")
    assert settings.log_format == "text"
    assert settings.log_level == "WARNING"
    assert settings.trusted_proxy_hops == 1


def test_load_settings_resolves_relative_path_from_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: リポジトリの外から起動する
    monkeypatch.chdir(tmp_path)

    # When
    settings = load_settings({"S7_DICTIONARY_PATH": "data/other.sqlite"})

    # Then: 作業ディレクトリではなくリポジトリ直下が基準になる
    assert settings.dictionary_path == REPO_ROOT / "data" / "other.sqlite"


def test_load_settings_empty_or_blank_value_uses_default() -> None:
    # Given: コンテナの設定では空で渡されることがある
    environ = {"PORT": "", "S7_DICTIONARY_PATH": "  ", "S7_LOG_FORMAT": "", "S7_LOG_LEVEL": " "}

    # When
    settings = load_settings(environ)

    # Then
    assert settings.port == 8000
    assert settings.dictionary_path == REPO_ROOT / "data" / "build" / "s7dict.sqlite"
    assert settings.log_format == "json"
    assert settings.log_level == "INFO"


def test_load_settings_strips_and_normalizes_case() -> None:
    # When
    settings = load_settings({"PORT": " 9000 ", "S7_LOG_FORMAT": "TEXT", "S7_LOG_LEVEL": "debug"})

    # Then
    assert settings.port == 9000
    assert settings.log_format == "text"
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PORT", "abc"),
        ("PORT", "1_000"),
        ("PORT", "８０００"),
        ("PORT", "0"),
        ("PORT", "65536"),
        ("S7_TRUSTED_PROXY_HOPS", "-1"),
        ("S7_TRUSTED_PROXY_HOPS", "1.5"),
        ("S7_LOG_FORMAT", "xml"),
        ("S7_LOG_LEVEL", "TRACE"),
    ],
)
def test_load_settings_invalid_value_raises_with_name_only(name: str, value: str) -> None:
    # When / Then: メッセージには環境変数の名前だけが入り、値は入らない
    with pytest.raises(ValueError, match=name) as exc_info:
        load_settings({name: value})
    assert value not in str(exc_info.value)
