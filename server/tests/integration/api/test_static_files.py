"""画面の静的ファイルの配信と、パスごとの Cache-Control(architecture.md「HTTPヘッダー」)。"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from s7.config import load_settings


@pytest.fixture
def web_client(make_app: Callable[..., FastAPI], tmp_path: Path) -> Iterator[TestClient]:
    # Given: 画面のビルド結果
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>S+7</title>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    app = make_app(load_settings({"S7_STATIC_DIR": str(tmp_path)}))
    with TestClient(app) as client:
        assert app.state.ready.wait(timeout=5)
        yield client


@pytest.mark.parametrize("path", ["/", "/about"])
def test_index_html_for_screen_paths(web_client: TestClient, path: str) -> None:
    response = web_client.get(path)

    assert response.status_code == 200
    assert "<title>S+7</title>" in response.text
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"


def test_hashed_assets_are_immutable(web_client: TestClient) -> None:
    response = web_client.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_other_static_files_are_no_cache(web_client: TestClient) -> None:
    response = web_client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"


def test_unknown_api_path_is_not_served_as_static(web_client: TestClient) -> None:
    response = web_client.get("/api/v1/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_api_still_works_with_static_files(web_client: TestClient) -> None:
    assert web_client.get("/api/v1/meta").status_code == 200
    assert web_client.get("/healthz").status_code == 200


def test_no_static_files_without_build(make_app: Callable[..., FastAPI], tmp_path: Path) -> None:
    """画面をビルドしていなければ配信しない(開発中は Vite の開発サーバーが配信する)。"""
    app = make_app(load_settings({"S7_STATIC_DIR": str(tmp_path / "missing")}))
    with TestClient(app) as client:
        assert client.get("/").status_code == 404
