"""POST /api/v1/events(匿名のアクセス解析)。"""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PAGE_VIEW_ID = "7f3a9c2e5b1d4a60"


@pytest.mark.parametrize(
    "event",
    [
        {"event": "page_view", "pageViewId": PAGE_VIEW_ID},
        {
            "event": "transform",
            "pageViewId": PAGE_VIEW_ID,
            "transformSeq": 2,
            "mode": "concept",
            "n": 7,
            "charsBucket": "le10000",
            "success": True,
            "nounCount": 412,
            "excludedCount": 0,
            "replacedCount": 371,
        },
        {
            "event": "transform",
            "pageViewId": PAGE_VIEW_ID,
            "transformSeq": 3,
            "mode": "gojuon",
            "n": 7,
            "charsBucket": "le1000",
            "success": False,
            "errorCode": "NETWORK_ERROR",
        },
        {"event": "copy", "pageViewId": PAGE_VIEW_ID, "transformSeq": 2},
    ],
)
def test_event_is_logged_as_analytics(
    capsys: pytest.CaptureFixture[str], client: TestClient, event: dict[str, Any]
) -> None:
    response = client.post("/api/v1/events", json=event)

    assert response.status_code == 204
    assert response.content == b""
    entries = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    [analytics] = [e for e in entries if e["kind"] == "analytics"]
    assert analytics["event"] == event


def test_unknown_fields_are_dropped(capsys: pytest.CaptureFixture[str], client: TestClient) -> None:
    event = {"event": "copy", "pageViewId": PAGE_VIEW_ID, "transformSeq": 1, "text": "本文"}

    assert client.post("/api/v1/events", json=event).status_code == 204

    output = capsys.readouterr().out
    assert "本文" not in output


@pytest.mark.parametrize(
    "event",
    [
        {"event": "unknown", "pageViewId": PAGE_VIEW_ID},
        {"event": "page_view", "pageViewId": "XYZ"},
        {"event": "page_view", "pageViewId": "7F3A9C2E5B1D4A60"},
        {"event": "copy", "pageViewId": PAGE_VIEW_ID, "transformSeq": 0},
        {"event": "copy", "pageViewId": PAGE_VIEW_ID, "transformSeq": "1"},
        {
            "event": "transform",
            "pageViewId": PAGE_VIEW_ID,
            "transformSeq": 1,
            "mode": "gojuon",
            "n": 7,
            "charsBucket": "le1000",
            "success": False,
            "errorCode": "SOMETHING_ELSE",
        },
        {
            "event": "transform",
            "pageViewId": PAGE_VIEW_ID,
            "transformSeq": 1,
            "mode": "gojuon",
            "n": 7,
            "charsBucket": "over50000",
            "success": True,
        },
    ],
)
def test_invalid_event_is_400(client: TestClient, event: dict[str, Any]) -> None:
    response = client.post("/api/v1/events", json=event)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_events_are_accepted_while_loading(make_app: Callable[..., FastAPI]) -> None:
    """辞書を使わないため、起動中も受け付ける。"""
    app = make_app(
        load_services=lambda _: (_ for _ in ()).throw(RuntimeError()),
        on_load_failure=lambda _: None,
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/events", json={"event": "page_view", "pageViewId": PAGE_VIEW_ID}
        )

    assert response.status_code == 204
