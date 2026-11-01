from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from s7.api.routers.docs import add_header


def test_docs_page_has_site_header(make_app: Callable[..., FastAPI]) -> None:
    # Given
    client = TestClient(make_app())

    # When
    response = client.get("/api/docs")

    # Then: 画面と同じ見出しの帯とメニューがあり、ほかのページへ移れる
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    html = response.text
    assert '<header class="s7-header">' in html
    assert 'role="img" aria-label="S+7メーカー"' in html
    assert '<a href="/" class="s7-transform">変換する</a>' in html
    assert '<a href="/about" class="s7-about">このアプリについて</a>' in html
    assert 'href="/api/docs" class="s7-api" aria-current="page"' in html


def test_docs_page_keeps_swagger_ui(make_app: Callable[..., FastAPI]) -> None:
    # Given
    client = TestClient(make_app())

    # When
    html = client.get("/api/docs").text

    # Then: Swagger UI の本体と OpenAPI の場所は変わらない
    assert "swagger-ui-bundle.js" in html
    assert '<div id="swagger-ui">' in html
    assert "/api/openapi.json" in html
    assert html.index('<header class="s7-header">') < html.index('<div id="swagger-ui">')


def test_docs_page_is_not_in_openapi(make_app: Callable[..., FastAPI]) -> None:
    # Given
    client = TestClient(make_app())

    # When
    spec = client.get("/api/openapi.json").json()

    # Then
    assert "/api/docs" not in spec["paths"]


@pytest.mark.parametrize(
    "html",
    ["<html><body></body></html>", "<html><head></head></html>"],
)
def test_add_header_fails_when_markers_are_missing(html: str) -> None:
    # FastAPI の更新で Swagger UI の HTML の形が変わったら、黙って帯を落とさずに失敗する
    with pytest.raises(ValueError, match="1つではありません"):
        add_header(html)
