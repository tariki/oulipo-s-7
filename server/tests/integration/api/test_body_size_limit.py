"""本文の大きさの上限(1MB)。Content-Length あり・chunked の両方。"""

import json
from collections.abc import Iterator

from fastapi.testclient import TestClient

LIMIT = 1_048_576


def _body_of_size(size: int) -> bytes:
    """ちょうど size バイトの、検証を通る本文(text を空白で埋める)。"""
    head = json.dumps({"mode": "gojuon", "text": "猫"}).encode()[:-2]  # 末尾の '"}' を除く
    padding = size - len(head) - 2
    return head + b" " * padding + b'"}'


def test_body_over_limit_with_content_length_is_413(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transform",
        content=b"x" * (LIMIT + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_body_at_limit_is_accepted(client: TestClient) -> None:
    body = _body_of_size(LIMIT)
    assert len(body) == LIMIT

    response = client.post(
        "/api/v1/transform", content=body, headers={"Content-Type": "application/json"}
    )

    # 本文の大きさでは断らない(text が50,000文字を超えるため、文字数で断る)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TEXT_TOO_LONG"


def _chunks(total: int, size: int = 65_536) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        chunk = min(size, total - sent)
        sent += chunk
        yield b"x" * chunk


def test_chunked_body_over_limit_is_413(client: TestClient) -> None:
    # Given: Content-Length の無い(chunked の)本文
    response = client.post(
        "/api/v1/transform",
        content=_chunks(LIMIT + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_chunked_body_within_limit_is_passed_through(client: TestClient) -> None:
    body = json.dumps({"text": "猫と犬", "mode": "gojuon", "n": 1}).encode()

    response = client.post(
        "/api/v1/transform",
        content=iter([body[:10], body[10:]]),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "三毛猫とキツネ"


def test_maximum_valid_request_fits_in_limit(client: TestClient) -> None:
    """50,000文字(補助面の文字)を \\uXXXX で書き、指定を各1,000個付けても413にならない。"""
    body = json.dumps(
        {
            "text": "🐈" * 50_000,
            "mode": "concept",
            "n": 99,
            "exclusions": list(range(999_000, 1_000_000)),
            "senseOverrides": {str(i): "90000011-n" for i in range(999_000, 1_000_000)},
        },
        ensure_ascii=True,
    ).encode()
    assert len(body) < LIMIT

    response = client.post(
        "/api/v1/transform", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 200
