import json
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from s7.config import load_settings


def test_healthz_returns_ok(make_app: Callable[..., FastAPI]) -> None:
    # Given
    client = TestClient(make_app())

    # When
    response = client.get("/healthz")

    # Then
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_is_not_in_openapi(make_app: Callable[..., FastAPI]) -> None:
    # Given
    client = TestClient(make_app())

    # When
    spec = client.get("/api/openapi.json").json()

    # Then: API仕様書には載せない
    assert "/healthz" not in spec["paths"]


def test_startup_and_shutdown_are_logged_as_json(
    make_app: Callable[..., FastAPI], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    app = make_app(load_settings({"S7_LOG_FORMAT": "json"}))

    # When: lifespan を動かし、辞書の読み込みが終わるのを待つ
    with TestClient(app):
        assert app.state.ready.wait(timeout=5)

    # Then
    entries = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [(e["kind"], e["message"]) for e in entries] == [
        ("app", "起動しました"),
        ("app", "辞書を読み込みました"),
        ("app", "終了しました"),
    ]
