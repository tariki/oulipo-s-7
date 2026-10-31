"""POST /api/v1/transform の正常系。小さな辞書(small_repo)と語の一覧で区切る Tokenizer を使う。"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from s7.services.meta_service import ATTRIBUTION

TEXT = "猫と犬と未知。"


def _post(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/v1/transform", json=body)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()
    return data


def _nouns(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in data["segments"] if s["type"] == "noun"]


def test_transform_gojuon(client: TestClient) -> None:
    # When
    data = _post(client, {"text": TEXT, "mode": "gojuon", "n": 1})

    # Then
    assert data["text"] == "三毛猫とキツネと未知。"
    assert data["segments"][1] == {"type": "text", "text": "と"}
    cat, _, unknown = _nouns(data)
    assert cat == {
        "type": "noun",
        "nounIndex": 0,
        "original": "猫",
        "replaced": "三毛猫",
        "status": "replaced",
        "lemma": "猫",
        "route": {
            "type": "gojuon",
            "fromIndex": 6,
            "toIndex": 7,
            "wrapped": False,
            "neighbors": [],
            "neighborsOmitted": 0,
        },
    }
    # 辞書に無い語は lemma・synsetId・route を持たない
    assert unknown == {
        "type": "noun",
        "nounIndex": 2,
        "original": "未知",
        "replaced": "未知",
        "status": "not_in_dictionary",
    }


def test_transform_concept_route(client: TestClient) -> None:
    data = _post(client, {"text": "三毛猫", "mode": "concept", "n": 1})

    [noun] = _nouns(data)
    assert (noun["status"], noun["replaced"], noun["synsetId"]) == (
        "climbed",
        "未登録語",
        "90000020-n",
    )
    route = noun["route"]
    assert route["type"] == "concept"
    assert route["climbs"] == [
        {
            "from": {"synsetId": "90000020-n", "lemma": "三毛猫", "definition": None},
            "to": {
                "synsetId": "90000011-n",
                "lemma": "ネコ",
                "definition": "ネコ科の動物；家で飼われる",
            },
            "relation": "hypernym",
        }
    ]
    # 見出し語の無い上位語も lemma・definition を null で必ず持つ
    assert route["parent"] == {"synsetId": "90000010-n", "lemma": None, "definition": None}
    assert route["from"]["synsetId"] == "90000011-n"
    assert (route["groupSize"], route["wrapped"]) == (4, False)


def test_transform_meta(client: TestClient) -> None:
    data = _post(client, {"text": TEXT, "mode": "concept"})

    assert data["meta"] == {
        "mode": "concept",
        "n": 7,  # 省略時は7
        "nounCount": 3,
        "excludedCount": 0,
        "replacedCount": 2,
        "ignoredExclusions": [],
        "ignoredSenseOverrides": [],
        "dictionaryVersion": data["meta"]["dictionaryVersion"],
        "attribution": ATTRIBUTION,
    }


def test_transform_exclusions_and_sense_overrides(client: TestClient) -> None:
    data = _post(
        client,
        {
            "text": TEXT,
            "mode": "concept",
            "n": 1,
            "exclusions": [1, 1, 50],
            "senseOverrides": {"0": "90000040-n", "2": "90000011-n", "9": "90000011-n"},
        },
    )

    cat, dog, _ = _nouns(data)
    assert (cat["synsetId"], cat["replaced"]) == ("90000040-n", "犬")
    assert (dog["status"], dog["replaced"], dog["synsetId"]) == ("excluded", "犬", "90000041-n")
    assert "route" not in dog
    assert data["meta"]["excludedCount"] == 1
    assert data["meta"]["ignoredExclusions"] == [50]  # 重複は1つとして扱う
    assert data["meta"]["ignoredSenseOverrides"] == [2, 9]


@pytest.mark.parametrize(
    "text",
    [
        "猫🐈と\n犬　ネコ。",  # 絵文字、改行、全角空白
        "👨‍👩‍👧猫",  # ゼロ幅接合子でつないだ絵文字
        "猫",
        " 猫 ",
    ],
)
@pytest.mark.parametrize("mode", ["gojuon", "concept"])
def test_segments_join_back_to_input(client: TestClient, text: str, mode: str) -> None:
    data = _post(client, {"text": text, "mode": mode, "n": 3})

    originals = "".join(
        s["text"] if s["type"] == "text" else s["original"] for s in data["segments"]
    )
    replaced = "".join(
        s["text"] if s["type"] == "text" else s["replaced"] for s in data["segments"]
    )
    assert originals == text
    assert replaced == data["text"]
    assert all(s["text"] for s in data["segments"] if s["type"] == "text")  # 空の文字列は無い


def test_transform_ignores_unknown_fields(client: TestClient) -> None:
    """知らない項目は無視する(APIの互換性)。"""
    data = _post(client, {"text": "猫", "mode": "gojuon", "future": {"x": 1}})

    assert data["meta"]["nounCount"] == 1


def test_transform_accepts_maximum_values(client: TestClient) -> None:
    data = _post(
        client,
        {
            "text": "猫" * 50_000,
            "mode": "gojuon",
            "n": 99,
            "exclusions": list(range(1_000)),
            "senseOverrides": {str(i): "90000011-n" for i in range(1_000)},
        },
    )

    assert data["meta"]["nounCount"] == 50_000
    assert data["meta"]["excludedCount"] == 1_000
