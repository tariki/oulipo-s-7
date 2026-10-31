"""利用制限の回数と文字数の429と Retry-After(機能設計書「RateLimiter」)。"""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from s7.api.middleware.rate_limiter import RateLimiter
from s7.config import load_settings


def test_transform_count_limit(client: TestClient) -> None:
    # Given: 変換などの枠(30回/分)を使い切る。語義の一覧も同じ枠
    for _ in range(15):
        assert (
            client.post("/api/v1/transform", json={"text": "猫", "mode": "gojuon"}).status_code
            == 200
        )
        assert client.get("/api/v1/senses", params={"lemma": "猫"}).status_code == 200

    # When
    response = client.post("/api/v1/transform", json={"text": "猫", "mode": "gojuon"})

    # Then
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert response.json()["error"]["details"] == {
        "retryAfter": int(response.headers["Retry-After"])
    }
    # 画面の補助の枠は別
    assert client.get("/api/v1/meta").status_code == 200


def test_chars_limit_is_checked_after_validation(make_app: Callable[..., FastAPI]) -> None:
    # Given: 文字数の上限を小さくした利用制限
    app = make_app()
    app.state.rate_limiter = RateLimiter(chars_per_minute=10)
    with TestClient(app) as client:
        assert app.state.ready.wait(timeout=5)
        body = {"text": "猫" * 6, "mode": "gojuon"}
        assert client.post("/api/v1/transform", json=body).status_code == 200

        # When: 合計が上限を超える
        over = client.post("/api/v1/transform", json=body)
        # 入力検証で断るリクエストは、文字数の枠を使わない
        invalid = client.post("/api/v1/transform", json={"text": "猫" * 6, "mode": "x"})

    # Then
    assert over.status_code == 429
    assert over.headers["Retry-After"] == "60"
    assert invalid.status_code == 400


def test_preflight_is_not_counted(client: TestClient) -> None:
    for _ in range(40):
        response = client.options(
            "/api/v1/transform",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code == 200

    assert (
        client.post("/api/v1/transform", json={"text": "猫", "mode": "gojuon"}).status_code == 200
    )


def test_trusted_proxy_uses_forwarded_address(make_app: Callable[..., FastAPI]) -> None:
    # Given: 1段のプロキシを信頼する
    app = make_app(load_settings({"S7_TRUSTED_PROXY_HOPS": "1"}))
    with TestClient(app) as client:
        assert app.state.ready.wait(timeout=5)

        # When: 利用者Aが変換などの枠を使い切る
        for _ in range(30):
            client.get("/api/v1/senses?lemma=猫", headers={"X-Forwarded-For": "203.0.113.1"})
        limited = client.get("/api/v1/senses?lemma=猫", headers={"X-Forwarded-For": "203.0.113.1"})
        # 先頭を偽装しても、プロキシが付けた末尾の値で数える
        spoofed = client.get(
            "/api/v1/senses?lemma=猫", headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.1"}
        )
        other = client.get("/api/v1/senses?lemma=猫", headers={"X-Forwarded-For": "203.0.113.2"})

    # Then
    assert (limited.status_code, spoofed.status_code, other.status_code) == (429, 429, 200)


def test_startup_503_is_not_counted(make_app: Callable[..., FastAPI]) -> None:
    """起動中の503は利用制限の回数に数えない(StartupGate が先に返す)。"""
    app = make_app(
        load_services=lambda _: (_ for _ in ()).throw(RuntimeError()),
        on_load_failure=lambda _: None,
    )
    with TestClient(app) as client:
        for _ in range(35):
            assert client.get("/api/v1/senses?lemma=猫").status_code == 503

    assert app.state.rate_limiter.key_count() == 0
