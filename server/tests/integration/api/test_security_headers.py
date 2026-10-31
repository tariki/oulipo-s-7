"""セキュリティヘッダーとgzip(architecture.md「HTTPヘッダー」)。"""

import pytest
from fastapi.testclient import TestClient

COMMON = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000",
}


@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("GET", "/api/v1/meta", 200),
        ("GET", "/api/v1/senses?lemma=存在しない", 404),
        ("GET", "/healthz", 200),
    ],
)
def test_api_responses_have_security_headers_and_no_store(
    client: TestClient, method: str, path: str, status: int
) -> None:
    response = client.request(method, path)

    assert response.status_code == status
    for name, value in COMMON.items():
        assert response.headers[name] == value
    assert response.headers["Cache-Control"] == "no-store"
    assert "Content-Security-Policy" not in response.headers  # 画面だけに付ける


def test_api_docs_have_no_csp_or_no_store(client: TestClient) -> None:
    """API仕様書は外部のスクリプトを読み込むため、CSP を付けない。"""
    response = client.get("/api/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
    assert "Cache-Control" not in response.headers


def test_large_response_is_gzipped(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transform",
        json={"text": "猫と犬。" * 500, "mode": "gojuon"},
        headers={"Accept-Encoding": "gzip"},
    )

    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "gzip"
