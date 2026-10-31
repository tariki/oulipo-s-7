"""GET /api/v1/senses と GET /api/v1/meta。"""

from fastapi.testclient import TestClient

from s7.services.meta_service import ATTRIBUTION


def test_senses_lists_definitions_and_lemmas(client: TestClient) -> None:
    response = client.get("/api/v1/senses", params={"lemma": "猫"})

    assert response.status_code == 200
    assert response.json() == {
        "lemma": "猫",
        "senses": [
            {
                "synsetId": "90000011-n",
                "rank": 0,
                "definition": "ネコ科の動物；家で飼われる",
                "lemmas": ["ネコ", "猫"],
            },
            {"synsetId": "90000040-n", "rank": 1, "definition": None, "lemmas": ["猫"]},
        ],
    }


def test_meta_returns_limits_and_attribution(client: TestClient) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["limits"] == {
        "maxChars": 50_000,
        "nMin": 1,
        "nMax": 99,
        "maxExclusions": 1_000,
        "maxSenseOverrides": 1_000,
        "transformRequestsPerMinute": 30,
        "auxiliaryRequestsPerMinute": 120,
        "charsPerMinute": 200_000,
    }
    assert body["attribution"] == ATTRIBUTION
    assert body["dictionaryVersion"]


def test_openapi_has_description_and_paths(client: TestClient) -> None:
    spec = client.get("/api/openapi.json").json()

    assert "## エラーコード" in spec["info"]["description"]
    assert {"/api/v1/transform", "/api/v1/senses", "/api/v1/meta"} <= set(spec["paths"])
