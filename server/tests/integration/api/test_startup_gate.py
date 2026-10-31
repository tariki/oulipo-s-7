"""辞書の読み込み中の503(StartupGate)と、読み込みの失敗。"""

import json
import os
import threading
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from s7.api.dependencies import Services
from s7.app import create_app
from s7.config import Settings, load_settings
from s7.repositories.dictionary_repository import DictionaryRepository

from .conftest import build_services


def test_api_returns_503_while_loading(
    make_app: Callable[..., FastAPI], small_repo: DictionaryRepository
) -> None:
    # Given: 読み込みが release されるまで終わらない
    release = threading.Event()

    def slow_load(_: Settings) -> Services:
        release.wait(timeout=5)
        return build_services(small_repo)

    app = make_app(load_services=slow_load)
    with TestClient(app) as client:
        # When / Then: 読み込み中
        for method, path in [
            ("POST", "/api/v1/transform"),
            ("GET", "/api/v1/meta"),
            ("GET", "/api/v1/senses?lemma=猫"),
        ]:
            response = client.request(method, path, json={"text": "猫", "mode": "gojuon"})
            assert response.status_code == 503
            assert response.headers["Retry-After"] == "1"
            assert response.json()["error"]["code"] == "SERVICE_STARTING"
        assert client.get("/healthz").status_code == 200  # 起動確認は読み込みを待たない
        # 辞書を使わない /api/v1/events は503にしない(ルーターはフェーズBで作る)
        assert client.post("/api/v1/events", json={}).status_code != 503

        # When: 読み込みが終わる
        release.set()
        assert app.state.ready.wait(timeout=5)

        # Then
        assert client.get("/api/v1/meta").status_code == 200
        assert (
            client.post("/api/v1/transform", json={"text": "猫", "mode": "gojuon"}).status_code
            == 200
        )


def test_load_failure_is_logged_and_handled(
    make_app: Callable[..., FastAPI], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    failures: list[BaseException] = []
    done = threading.Event()

    def broken_load(_: Settings) -> Services:
        raise FileNotFoundError("/secret/path/s7dict.sqlite")

    def on_failure(error: BaseException) -> None:
        failures.append(error)
        done.set()

    app = make_app(load_services=broken_load, on_load_failure=on_failure)

    # When
    with TestClient(app) as client:
        assert done.wait(timeout=5)
        status = client.get("/api/v1/meta").status_code

    # Then: 読み込みの失敗を処理し、APIは503のまま
    assert isinstance(failures[0], FileNotFoundError)
    assert status == 503
    output = capsys.readouterr().out
    [error] = [json.loads(line) for line in output.splitlines() if '"ERROR"' in line]
    assert (error["message"], error["exceptionType"]) == (
        "辞書の読み込みに失敗しました",
        "FileNotFoundError",
    )
    assert "/secret/path" not in output


def test_default_load_failure_terminates_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """既定では、読み込みに失敗したらプロセスを終えてホスティング先に再起動させる。"""
    # Given: 変換用辞書が無い
    exit_codes: list[int] = []
    exited = threading.Event()

    def fake_exit(code: int) -> None:
        exit_codes.append(code)
        exited.set()

    monkeypatch.setattr(os, "_exit", fake_exit)
    app = create_app(load_settings({"S7_DICTIONARY_PATH": f"{tmp_path}/missing.sqlite"}))

    # When
    with TestClient(app):
        assert exited.wait(timeout=10)

    # Then
    assert exit_codes == [1]
