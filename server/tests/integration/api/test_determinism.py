"""同じ入力を2回送って同じ結果になる(PRDの信頼性要件)。"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("mode", ["gojuon", "concept"])
def test_same_request_returns_same_response(client: TestClient, mode: str) -> None:
    body = {"text": "猫と犬と三毛猫とル・コルビュジエと未知。" * 20, "mode": mode, "n": 7}

    first = client.post("/api/v1/transform", json=body)
    second = client.post("/api/v1/transform", json=body)

    assert first.status_code == 200
    assert first.content == second.content
