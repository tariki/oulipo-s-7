import json
import logging
import re

import pytest

from s7.logging_config import configure_logging, log_app

ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def read_json_lines(capsys: pytest.CaptureFixture[str]) -> list[dict[str, object]]:
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines()]


def test_log_app_json_has_required_fields(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "INFO")

    # When
    log_app("起動しました", dictionary_version="2026.10.0", lemma_count=3)

    # Then: 1行1つのJSONで、必須の4項目と、camelCaseにした追加の項目を持つ
    [entry] = read_json_lines(capsys)
    assert isinstance(entry["time"], str)
    assert ISO_UTC.match(entry["time"])
    assert entry["severity"] == "INFO"
    assert entry["kind"] == "app"
    assert entry["message"] == "起動しました"
    assert entry["dictionaryVersion"] == "2026.10.0"
    assert entry["lemmaCount"] == 3


def test_log_app_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "WARNING")

    # When
    log_app("出ない")
    log_app("出る", severity="WARNING")

    # Then
    entries = read_json_lines(capsys)
    assert [e["message"] for e in entries] == ["出る"]
    assert entries[0]["severity"] == "WARNING"


def test_extra_fields_cannot_override_required_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    configure_logging("json", "INFO")

    # When: 必須の項目と同じ名前を追加の項目に渡す
    log_app("起動しました", kind="request", severity_note="x", time="dummy")

    # Then: 必須の項目は変わらない
    [entry] = read_json_lines(capsys)
    assert entry["kind"] == "app"
    assert entry["time"] != "dummy"
    assert entry["severityNote"] == "x"


def test_snake_case_with_several_parts_becomes_camel_case(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    configure_logging("json", "INFO")

    # When
    log_app("x", noun_excluded_count=1)

    # Then
    [entry] = read_json_lines(capsys)
    assert entry["nounExcludedCount"] == 1


def test_configure_logging_twice_keeps_single_handler(capsys: pytest.CaptureFixture[str]) -> None:
    # Given: 2回設定する(テストやリロードで起こりうる)
    configure_logging("json", "INFO")
    configure_logging("json", "INFO")

    # When
    log_app("1回だけ出る")

    # Then
    assert len(read_json_lines(capsys)) == 1
    assert len(logging.getLogger().handlers) == 1


def test_text_format_exception_stays_on_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("text", "INFO")

    # When: メッセージに改行があり、例外も付く
    try:
        raise ValueError("吾輩は猫である")
    except ValueError:
        logging.getLogger("uvicorn.error").exception("1行目\n2行目")

    # Then: 1行で、例外のメッセージは出さず、ファイル名だけを出す
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert "吾輩は猫である" not in out
    assert 'exceptionType="ValueError"' in out
    assert "test_logging_config.py:" in out
    assert "/workspaces/" not in out


def test_debug_level_outputs_debug_severity(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "DEBUG")

    # When
    log_app("詳細", severity="DEBUG")

    # Then
    [entry] = read_json_lines(capsys)
    assert entry["severity"] == "DEBUG"


def test_text_format_is_single_readable_line(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("text", "INFO")

    # When
    log_app("起動しました", port=8000)

    # Then
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    assert re.match(r"^\S+Z INFO app 起動しました port=8000$", out.strip())


def test_uvicorn_error_logger_uses_same_format(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "INFO")

    # When: Uvicornが自分のロガーに出したログ
    logging.getLogger("uvicorn.error").info("Started server process")

    # Then
    [entry] = read_json_lines(capsys)
    assert entry["kind"] == "app"
    assert entry["message"] == "Started server process"


def test_uvicorn_access_logger_is_silenced(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "INFO")

    # When: アクセスログにはクエリ文字列(見出し語)が入りうる
    logging.getLogger("uvicorn.access").info("GET /api/v1/senses?lemma=猫")

    # Then
    assert capsys.readouterr().out == ""


def test_exception_logs_type_and_stack_without_message(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    configure_logging("json", "INFO")

    # When: 例外のメッセージに入力文が入っている
    try:
        raise ValueError("吾輩は猫である")
    except ValueError:
        logging.getLogger("uvicorn.error").exception("Exception in ASGI application")

    # Then: 型と場所だけを出し、メッセージは出さない
    out = capsys.readouterr().out
    assert "吾輩は猫である" not in out
    [entry] = [json.loads(line) for line in out.splitlines()]
    assert entry["severity"] == "ERROR"
    assert entry["exceptionType"] == "ValueError"
    assert isinstance(entry["stack"], list)
    assert entry["stack"]
