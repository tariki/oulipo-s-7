"""スナップショットテスト(マーカー snapshot。本物の変換用辞書が必要)。

標準の文章3本(data/standard-texts/)を両モード・N=7で変換し、期待値(expected/)と比べる。
辞書や変換の処理を変えて結果が変わったら、`pytest -m snapshot --update-snapshots` で期待値を
作り直し、差分が意図どおりかをプルリクエストに書く(開発ガイドライン「スナップショットの更新」)。

期待値は大きくなりすぎないよう要点だけにする(変換後の文章と、名詞ごとの元の語・変換後の語・状態)。
経路などの細部は、小さな辞書のテストで確かめる。
"""

import difflib
import json
from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient

from s7.config import REPO_ROOT
from s7builder.quality_report import list_standard_texts

pytestmark = pytest.mark.snapshot

EXPECTED_DIR: Final = Path(__file__).with_name("expected")
TEXTS: Final = list_standard_texts(REPO_ROOT / "data" / "standard-texts")
MODES: Final = ("gojuon", "concept")
N: Final = 7
#: 差分を表示する上限の行数(全部出すと読めないため)
_DIFF_LINES: Final = 40


def _dump(response: dict[str, object]) -> str:
    """期待値の形に書く。名詞は1行に1つにし、差分を読みやすくする。"""
    meta = response["meta"]
    segments = response["segments"]
    assert isinstance(meta, dict)
    assert isinstance(segments, list)
    header = {
        "dictionaryVersion": meta["dictionaryVersion"],
        "mode": meta["mode"],
        "n": meta["n"],
        "text": str(response["text"]).split("\n"),
    }
    nouns = [
        json.dumps([s["original"], s["replaced"], s["status"]], ensure_ascii=False)
        for s in segments
        if isinstance(s, dict) and s.get("type") == "noun"
    ]
    lines = ["{"]
    lines += [
        f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},"
        for key, value in header.items()
    ]
    lines.append('  "nouns": [')
    lines += [f"    {noun}," for noun in nouns[:-1]] + [f"    {noun}" for noun in nouns[-1:]]
    lines += ["  ]", "}"]
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("name", "text"), TEXTS, ids=[name for name, _ in TEXTS])
def test_snapshot_matches_expected(
    real_client: TestClient,
    request: pytest.FixtureRequest,
    name: str,
    text: str,
    mode: str,
) -> None:
    # Given
    expected_path = EXPECTED_DIR / f"{name}.{mode}.json"

    # When
    response = real_client.post("/api/v1/transform", json={"text": text, "mode": mode, "n": N})

    # Then
    assert response.status_code == 200
    actual = _dump(response.json())
    if request.config.getoption("--update-snapshots"):
        expected_path.write_text(actual, encoding="utf-8")
        return
    assert expected_path.is_file(), (
        f"期待値がありません: {expected_path}(--update-snapshots で作ってください)"
    )
    expected = expected_path.read_text(encoding="utf-8")
    if actual != expected:
        diff = difflib.unified_diff(
            expected.splitlines(), actual.splitlines(), "期待値", "今回の結果", lineterm=""
        )
        shown = "\n".join(list(diff)[:_DIFF_LINES])
        pytest.fail(
            f"{name}・{mode} の変換結果が期待値と違います。意図した変化なら"
            f" --update-snapshots で作り直してください。\n{shown}"
        )


QUALITY_REPORT: Final = REPO_ROOT / "data" / "reports" / "quality-report.json"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("name", "text"), TEXTS, ids=[name for name, _ in TEXTS])
def test_quality_report_matches_api(
    real_client: TestClient, name: str, text: str, mode: str
) -> None:
    """品質の報告の数が、API の変換結果と一致する。

    品質の報告(QualityReporter)はサーバーと同じ組み立てを自分で行うため、サーバー(app.py)の組み立てが
    変わったのに報告が古い組み立てのまま、という食い違いをここで見つける。
    """
    # Given
    report = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    entry = next(t for t in report["texts"] if t["name"] == name)[mode]

    # When
    meta = real_client.post("/api/v1/transform", json={"text": text, "mode": mode, "n": N}).json()[
        "meta"
    ]

    # Then
    assert report["n"] == N
    assert (entry["noun_count"], entry["replaced_count"]) == (
        meta["nounCount"],
        meta["replacedCount"],
    )


def test_snapshot_texts_exist() -> None:
    """標準の文章が3本あること(ファイルを消したことに気付けるように)。"""
    assert [name for name, _ in TEXTS] == ["chumon", "rashomon", "wagahai"]
