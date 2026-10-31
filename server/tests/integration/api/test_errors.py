"""エラーコードの一覧と、入力の型の厳しさ(機能設計書「入力の型の厳しさ」「エラーレスポンスの形式」)。"""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _error(response: Any) -> dict[str, Any]:
    error: dict[str, Any] = response.json()["error"]
    return error


@pytest.mark.parametrize(
    ("body", "code"),
    [
        # text
        ({"mode": "gojuon"}, "TEXT_EMPTY"),
        ({"text": "", "mode": "gojuon"}, "TEXT_EMPTY"),
        ({"text": " 　\n\t", "mode": "gojuon"}, "TEXT_EMPTY"),
        ({"text": 1, "mode": "gojuon"}, "INVALID_REQUEST"),
        ({"text": None, "mode": "gojuon"}, "INVALID_REQUEST"),
        # mode
        ({"text": "猫"}, "INVALID_MODE"),
        ({"text": "猫", "mode": "other"}, "INVALID_MODE"),
        ({"text": "猫", "mode": 1}, "INVALID_MODE"),
        # n
        ({"text": "猫", "mode": "gojuon", "n": "7"}, "INVALID_N"),
        ({"text": "猫", "mode": "gojuon", "n": 7.0}, "INVALID_N"),
        ({"text": "猫", "mode": "gojuon", "n": True}, "INVALID_N"),
        ({"text": "猫", "mode": "gojuon", "n": 0}, "INVALID_N"),
        ({"text": "猫", "mode": "gojuon", "n": 100}, "INVALID_N"),
        # exclusions・senseOverrides の形式と個数
        ({"text": "猫", "mode": "gojuon", "exclusions": 1}, "INVALID_REQUEST"),
        ({"text": "猫", "mode": "gojuon", "exclusions": [-1]}, "INVALID_REQUEST"),
        ({"text": "猫", "mode": "gojuon", "exclusions": ["1"]}, "INVALID_REQUEST"),
        ({"text": "猫", "mode": "gojuon", "exclusions": list(range(1_001))}, "INVALID_REQUEST"),
        (
            {"text": "猫", "mode": "gojuon", "senseOverrides": {"01": "90000011-n"}},
            "INVALID_REQUEST",
        ),
        (
            {"text": "猫", "mode": "gojuon", "senseOverrides": {"a": "90000011-n"}},
            "INVALID_REQUEST",
        ),
        (
            {"text": "猫", "mode": "gojuon", "senseOverrides": {"0": "90000011-v"}},
            "INVALID_REQUEST",
        ),
        (
            {
                "text": "猫",
                "mode": "gojuon",
                "senseOverrides": {str(i): "90000011-n" for i in range(1_001)},
            },
            "INVALID_REQUEST",
        ),
        # 本文がオブジェクトでない
        ([], "INVALID_REQUEST"),
    ],
)
def test_invalid_body_is_400(client: TestClient, body: object, code: str) -> None:
    response = client.post("/api/v1/transform", json=body)

    assert response.status_code == 400
    assert _error(response)["code"] == code
    assert _error(response)["message"]


def test_text_too_long_reports_counts(client: TestClient) -> None:
    # Given: 補助面の文字(サロゲートペア)も1文字と数える
    text = "🐈" * 50_001

    # When
    response = client.post("/api/v1/transform", json={"text": text, "mode": "gojuon"})

    # Then
    assert response.status_code == 400
    error = _error(response)
    assert error["code"] == "TEXT_TOO_LONG"
    assert error["details"] == {"maxChars": 50_000, "actualChars": 50_001}
    assert "50,001" in error["message"]


def test_lone_surrogate_is_invalid_request(client: TestClient) -> None:
    """JSONの \\ud800 のような書き方で送れる単独のサロゲートは、入力検証で断る。"""
    body = '{"text": "\\u732b\\ud800", "mode": "gojuon"}'

    response = client.post(
        "/api/v1/transform", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert _error(response)["code"] == "INVALID_REQUEST"


def test_malformed_json_is_invalid_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transform",
        content=b'{"text": "\xe7\x8c',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert _error(response)["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("query", ["", "?lemma=", "?lemma=" + "猫" * 101])
def test_senses_invalid_lemma_is_400(client: TestClient, query: str) -> None:
    response = client.get(f"/api/v1/senses{query}")

    assert response.status_code == 400
    assert _error(response)["code"] == "INVALID_REQUEST"


def test_senses_unknown_lemma_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/senses", params={"lemma": "存在しない"})

    assert response.status_code == 404
    assert _error(response)["code"] == "LEMMA_NOT_FOUND"


def test_unexpected_error_is_500_without_internal_details(
    make_app: Callable[..., FastAPI],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: 変換の中で、本文を含むメッセージの例外が起きる
    def broken(text: str, *args: object, **kwargs: object) -> None:
        raise RuntimeError(f"失敗: {text}")

    app = make_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        assert app.state.ready.wait(timeout=5)
        monkeypatch.setattr(app.state.services.transform, "transform", broken)

        # When
        response = client.post("/api/v1/transform", json={"text": "秘密の本文", "mode": "gojuon"})

    # Then: 応答とログに本文も例外のメッセージも出ない
    assert response.status_code == 500
    assert _error(response) == {
        "code": "INTERNAL_ERROR",
        "message": "変換に失敗しました。時間をおいてお試しください",
    }
    output = capsys.readouterr().out
    assert "秘密" not in output
    entries = [json.loads(line) for line in output.splitlines()]
    [error_entry] = [e for e in entries if e["severity"] == "ERROR"]
    assert error_entry["exceptionType"] == "RuntimeError"
    [request_entry] = [e for e in entries if e["kind"] == "request"]
    assert (request_entry["status"], request_entry["errorCode"]) == (500, "INTERNAL_ERROR")
