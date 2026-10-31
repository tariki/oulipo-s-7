import threading

import pytest

from s7.api.middleware import rate_limiter
from s7.api.middleware.rate_limiter import RateLimiter, client_key
from s7.logging_config import configure_logging


class FakeClock:
    """進めた分だけ時刻が進む時計。"""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_count_limit_per_bucket(clock: FakeClock) -> None:
    # Given
    limiter = RateLimiter(clock=clock)

    # When: 変換などの枠は30回/分
    results = [limiter.check_count("a", "transform") for _ in range(31)]

    # Then
    assert results[:30] == [None] * 30
    assert results[30] == 60
    # 画面の補助の枠は別に数える(120回/分)
    assert all(limiter.check_count("a", "auxiliary") is None for _ in range(120))
    assert limiter.check_count("a", "auxiliary") is not None
    # 接続元ごとに数える
    assert limiter.check_count("b", "transform") is None


def test_rejected_requests_are_not_counted_and_window_slides(clock: FakeClock) -> None:
    # Given: 10秒ごとに3回ずつ、計30回受け付けた
    limiter = RateLimiter(clock=clock)
    for _ in range(10):
        for _ in range(3):
            assert limiter.check_count("a", "transform") is None
        clock.now += 5

    # When: 断られたリクエストは数えない
    assert limiter.check_count("a", "transform") == 10  # 最も古い記録(1,000秒)が60秒の外に出るまで
    clock.now = 1_060.0

    # Then: 最も古い3回が窓の外に出たので、3回だけ受け付ける
    assert [limiter.check_count("a", "transform") for _ in range(4)] == [None, None, None, 5]


def test_retry_after_is_ceiled_and_at_least_one(clock: FakeClock) -> None:
    limiter = RateLimiter(clock=clock)
    for _ in range(30):
        limiter.check_count("a", "transform")

    clock.now += 59.2
    assert limiter.check_count("a", "transform") == 1  # 0.8秒 → 切り上げて1
    clock.now += 0.79
    assert limiter.check_count("a", "transform") == 1  # 0.01秒でも最小1


def test_chars_limit(clock: FakeClock) -> None:
    # Given: 200,000文字/分
    limiter = RateLimiter(clock=clock)
    assert limiter.check_chars("a", 50_000) is None
    clock.now += 10
    assert limiter.check_chars("a", 50_000) is None
    clock.now += 10
    assert limiter.check_chars("a", 50_000) is None
    clock.now += 10
    assert limiter.check_chars("a", 40_000) is None  # 合計190,000

    # When / Then: 合計 + 今回が上限を超えるなら断り、今回の分は加えない
    assert limiter.check_chars("a", 20_000) == 30  # 最も古い50,000文字が出るまで(1,060 - 1,030)
    assert limiter.check_chars("a", 10_000) is None  # ちょうど200,000文字は受け付ける


def test_chars_retry_after_waits_until_enough_leaves(clock: FakeClock) -> None:
    limiter = RateLimiter(clock=clock)
    for _ in range(4):
        limiter.check_chars("a", 50_000)
        clock.now += 10

    # 50,000文字を足すには、最も古い1件(1,000秒)が出ればよい → 1,060 - 1,040 = 20
    assert limiter.check_chars("a", 50_000) == 20


def test_least_recently_used_key_is_dropped(clock: FakeClock) -> None:
    # Given: キーは2個まで
    limiter = RateLimiter(clock=clock, max_keys=2)
    limiter.check_count("a", "transform")
    limiter.check_count("b", "transform")
    limiter.check_count("a", "transform")  # a を使い直す

    # When
    limiter.check_count("c", "transform")

    # Then: 最も長く使われていない b を捨てた
    assert limiter.key_count() == 2
    for _ in range(28):
        assert limiter.check_count("a", "transform") is None  # a の記録は残っている(2回 + 28回)
    assert limiter.check_count("a", "transform") is not None


def test_sweep_drops_expired_keys(clock: FakeClock) -> None:
    limiter = RateLimiter(clock=clock)
    limiter.check_count("a", "transform")
    limiter.check_chars("b", 10)

    clock.now += 61
    limiter.check_count("c", "auxiliary")  # 1分ごとの掃除が走る

    assert limiter.key_count() == 1


def _scope(client: str, forwarded: str | None = None) -> dict[str, object]:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    return {"type": "http", "client": (client, 1234), "headers": headers}


@pytest.mark.parametrize(
    ("scope", "hops", "key"),
    [
        (_scope("203.0.113.5"), 0, "203.0.113.5"),
        # IPv6 は先頭64ビット
        (_scope("2001:db8:1:2:3:4:5:6"), 0, "2001:db8:1:2::/64"),
        # 信頼するプロキシが1段: 末尾の値(先頭の偽装は無視する)
        (_scope("10.0.0.1", "198.51.100.9, 203.0.113.5"), 1, "203.0.113.5"),
        (_scope("10.0.0.1", "198.51.100.9, 203.0.113.5, 10.0.0.2"), 2, "203.0.113.5"),
        (_scope("10.0.0.1", "2001:db8::1"), 1, "2001:db8::/64"),
        # IPv4射影アドレス(デュアルスタックで待ち受けたとき)は IPv4 として扱う
        (_scope("::ffff:203.0.113.5"), 0, "203.0.113.5"),
        (_scope("10.0.0.1", "::ffff:203.0.113.5"), 1, "203.0.113.5"),
        # 読めないアドレスの直接の接続元(テストのクライアントなど)はそのまま
        (_scope("testclient"), 0, "testclient"),
    ],
)
def test_client_key(scope: dict[str, object], hops: int, key: str) -> None:
    assert client_key(scope, hops) == key


@pytest.mark.parametrize("forwarded", [None, "", "not-an-ip", "203.0.113.5"])
def test_client_key_falls_back_to_direct_address_with_warning(
    forwarded: str | None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rate_limiter, "_last_warning", [])
    # Given: 2段のプロキシを信頼するのに、X-Forwarded-For が無い・足りない・読めない

    configure_logging("json", "INFO")

    # When
    key = client_key(_scope("10.0.0.1", forwarded), 2)

    # Then: 直接の接続元を使い、WARNING を出す(IPアドレスは出さない)
    assert key == "10.0.0.1"
    output = capsys.readouterr().out
    assert '"WARNING"' in output
    assert "10.0.0.1" not in output


def test_client_key_reads_all_forwarded_header_lines() -> None:
    """プロキシが値を別の行で足した場合も、すべての行を順につなげて末尾から数える。"""
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 1234),
        "headers": [(b"x-forwarded-for", b"198.51.100.9"), (b"x-forwarded-for", b"203.0.113.5")],
    }

    assert client_key(scope, 1) == "203.0.113.5"


def test_forwarded_warning_is_at_most_once_per_minute(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rate_limiter, "_last_warning", [])
    configure_logging("json", "INFO")

    for _ in range(5):
        client_key(_scope("10.0.0.1"), 1)

    assert capsys.readouterr().out.count('"WARNING"') == 1


def test_limiter_counts_correctly_from_many_threads() -> None:
    """回数(イベントループ)と文字数(スレッド)から同時に呼ばれても、数え漏れや数えすぎが無い。"""
    limiter = RateLimiter()
    accepted: list[bool] = []

    def run() -> None:
        for _ in range(20):
            accepted.append(limiter.check_count("a", "auxiliary") is None)
            limiter.check_chars("a", 1)

    threads = [threading.Thread(target=run) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert accepted.count(True) == 120
