"""CORS(機能設計書「API設計」の共通事項)。413・429・503 の応答にも付く。"""

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

ORIGIN = {"Origin": "https://other.example"}


def _assert_cors(response: Response) -> None:
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Access-Control-Expose-Headers"] == "Retry-After"


def test_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/v1/transform",
        headers={
            **ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-S7-Client",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert set(response.headers["Access-Control-Allow-Methods"].split(", ")) == {
        "GET",
        "POST",
        "OPTIONS",
    }
    assert response.headers["Access-Control-Max-Age"] == "86400"
    assert "x-s7-client" in response.headers["Access-Control-Allow-Headers"].lower()


def test_cors_on_200_400_and_413(client: TestClient) -> None:
    ok = client.post("/api/v1/transform", json={"text": "猫", "mode": "gojuon"}, headers=ORIGIN)
    invalid = client.post("/api/v1/transform", json={"text": "", "mode": "gojuon"}, headers=ORIGIN)
    too_large = client.post(
        "/api/v1/transform",
        content=b"x" * 1_048_577,
        headers={**ORIGIN, "Content-Type": "application/json"},
    )

    assert (ok.status_code, invalid.status_code, too_large.status_code) == (200, 400, 413)
    for response in (ok, invalid, too_large):
        _assert_cors(response)


def test_cors_on_429(client: TestClient) -> None:
    for _ in range(30):
        client.get("/api/v1/senses", params={"lemma": "猫"})

    response = client.get("/api/v1/senses", params={"lemma": "猫"}, headers=ORIGIN)

    assert response.status_code == 429
    _assert_cors(response)


@pytest.mark.parametrize("path", ["/api/v1/meta"])
def test_cors_on_503(make_app: Callable[..., FastAPI], path: str) -> None:
    app = make_app(
        load_services=lambda _: (_ for _ in ()).throw(RuntimeError()),
        on_load_failure=lambda _: None,
    )
    with TestClient(app) as client:
        response = client.get(path, headers=ORIGIN)

    assert response.status_code == 503
    _assert_cors(response)


def test_cors_on_500(make_app: Callable[..., FastAPI], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError

    app = make_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        assert app.state.ready.wait(timeout=5)
        monkeypatch.setattr(app.state.services.transform, "transform", broken)
        response = client.post(
            "/api/v1/transform", json={"text": "猫", "mode": "gojuon"}, headers=ORIGIN
        )

    assert response.status_code == 500
    _assert_cors(response)
