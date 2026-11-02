"""性能テスト(マーカー performance。本物の変換用辞書が必要)。

50,000文字の変換の処理(TransformService。名詞の抽出と置き換え)の時間を両モードで測り、95パーセンタイルが
上限以内であることを確かめる(docs/architecture.md「性能の目標」: 1秒以内)。
HTTP・応答のJSONの生成・圧縮は含めない(「予算の内訳」で別の項目。APIを20回呼ぶと文字数の利用制限に
かかるため、ここでは測らない)。
上限は環境変数 S7_PERF_LIMIT_SECONDS で変えられる(CIは速度がばらつくため2秒。性能の大きな劣化を
見つけるための値)。測った値は標準出力に出す(`pytest -s` で見える)。
"""

import gc
import math
import os
import statistics
import time
from typing import Final

import pytest
from fastapi.testclient import TestClient

from s7.api.dependencies import Services
from s7.config import REPO_ROOT
from s7.domain.transform import Mode
from s7builder.quality_report import list_standard_texts

pytestmark = pytest.mark.performance

TARGET_CHARS: Final = 50_000
#: 測る回数(PRDの測定条件: 各20回以上の95パーセンタイル)
RUNS: Final = 20
#: 数えない空回しの回数(最初の数回は、辞書やキャッシュが温まっていないため遅い)
WARMUP_RUNS: Final = 3
N: Final = 7
#: 標準の文章の50,000文字に含まれる名詞の数の下限(文章を読めなかったのに速く見えて通るのを防ぐ)
MIN_NOUNS: Final = 1_000


def _limit_seconds() -> float:
    return float(os.environ.get("S7_PERF_LIMIT_SECONDS", "1.0"))


def _text() -> str:
    """標準の文章3本をつなげて繰り返し、50,000文字に切る(同じ文の繰り返しより実際に近い)。"""
    joined = "\n".join(
        text for _, text in list_standard_texts(REPO_ROOT / "data" / "standard-texts")
    )
    repeated = joined * math.ceil(TARGET_CHARS / len(joined))
    return repeated[:TARGET_CHARS]


def _percentile_95(durations: list[float]) -> float:
    ordered = sorted(durations)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


@pytest.mark.parametrize("mode", ["gojuon", "concept"])
def test_transform_50000_chars_within_limit(real_client: TestClient, mode: Mode) -> None:
    # Given
    services: Services = real_client.app.state.services  # type: ignore[attr-defined]
    text = _text()
    assert len(text) == TARGET_CHARS
    for _ in range(WARMUP_RUNS):
        services.transform.transform(text, mode, N)
    gc.collect()

    # When
    durations: list[float] = []
    for _ in range(RUNS):
        started = time.perf_counter()
        result = services.transform.transform(text, mode, N)
        durations.append(time.perf_counter() - started)

    # Then
    assert result.meta.noun_count >= MIN_NOUNS
    p95 = _percentile_95(durations)
    print(  # noqa: T201  測った値を残す(性能に効く変更のプルリクエストに書くため)
        f"\n{mode}: 50,000文字 名詞{result.meta.noun_count}個 "
        f"中央値 {statistics.median(durations):.3f}秒 95パーセンタイル {p95:.3f}秒 "
        f"(上限 {_limit_seconds():.1f}秒、{RUNS}回)"
    )
    assert p95 <= _limit_seconds()
