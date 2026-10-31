"""ログの形式(機能設計書「ログの形式」)。標準出力の各行が構造化ログで、本文と見出し語を含まない。"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

PRIVATE_TEXT = "猫と犬の秘密の手紙"
_REQUIRED: dict[str, type] = {"time": str, "severity": str, "kind": str, "message": str}
_REQUEST_FIELDS: dict[str, type | tuple[type, ...]] = {
    "method": str,
    "path": str,
    "status": int,
    "durationMs": int,
    "client": (str, type(None)),
    "errorCode": (str, type(None)),
}


def _entries(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_every_line_is_structured_and_has_no_text(
    capsys: pytest.CaptureFixture[str], client: TestClient
) -> None:
    # When: 成功・入力の不備・語義の一覧(クエリ文字列に見出し語)を呼ぶ
    client.post(
        "/api/v1/transform",
        json={"text": PRIVATE_TEXT, "mode": "concept", "n": 3},
        headers={"X-S7-Client": "web"},
    )
    client.post("/api/v1/transform", json={"text": PRIVATE_TEXT, "mode": "x"})
    client.get("/api/v1/senses", params={"lemma": "猫"})
    client.get("/api/v1/meta")

    # Then
    entries = _entries(capsys)
    for entry in entries:
        for key, kind in _REQUIRED.items():
            assert isinstance(entry[key], kind)
    output = json.dumps(entries, ensure_ascii=False)
    assert "秘密" not in output
    assert "猫" not in output  # 本文の名詞も、クエリ文字列の見出し語も出さない

    requests = [e for e in entries if e["kind"] == "request"]
    assert [(r["path"], r["status"], r["errorCode"]) for r in requests] == [
        ("/api/v1/transform", 200, None),
        ("/api/v1/transform", 400, "INVALID_MODE"),
        ("/api/v1/senses", 200, None),
        ("/api/v1/meta", 200, None),
    ]
    for request in requests:
        for key, kinds in _REQUEST_FIELDS.items():
            assert isinstance(request[key], kinds)
    transform = requests[0]
    assert (transform["client"], transform["mode"], transform["n"], transform["chars"]) == (
        "web",
        "concept",
        3,
        len(PRIVATE_TEXT),
    )
    assert "mode" not in requests[1]  # 検証で断ったため、変換の項目は無い
    assert "mode" not in requests[3]


def test_non_api_paths_are_not_logged_as_request(
    capsys: pytest.CaptureFixture[str], client: TestClient
) -> None:
    client.get("/healthz")

    assert [e for e in _entries(capsys) if e["kind"] == "request"] == []
