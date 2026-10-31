from s7.domain import limits
from s7.services.meta_service import ATTRIBUTION, MetaService


def test_meta_returns_version_limits_and_attribution() -> None:
    meta = MetaService("2026.10.0").meta()

    assert meta.dictionary_version == "2026.10.0"
    assert meta.limits.max_chars == limits.MAX_CHARS == 50_000
    assert (meta.limits.n_min, meta.limits.n_max) == (1, 99)
    assert meta.limits.chars_per_minute == 200_000
    assert meta.attribution == ATTRIBUTION
    assert "/about#credits" in ATTRIBUTION
