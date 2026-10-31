import json

import pytest
from fastapi.testclient import TestClient

from s7.app import create_app
from s7.config import load_settings


def test_healthz_returns_ok() -> None:
    # Given
    client = TestClient(create_app(load_settings({})))

    # When
    response = client.get("/healthz")

    # Then
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_is_not_in_openapi() -> None:
    # Given
    client = TestClient(create_app(load_settings({})))

    # When
    spec = client.get("/api/openapi.json").json()

    # Then: API仕様書には載せない
    assert "/healthz" not in spec["paths"]


def test_startup_and_shutdown_are_logged_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    # Given
    app = create_app(load_settings({"S7_LOG_FORMAT": "json"}))

    # When: lifespan を動かす
    with TestClient(app):
        pass

    # Then
    entries = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [(e["kind"], e["message"]) for e in entries] == [
        ("app", "起動しました"),
        ("app", "終了しました"),
    ]
