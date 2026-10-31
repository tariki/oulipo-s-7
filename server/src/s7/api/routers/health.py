"""GET /healthz(HealthRouter)。

HTTPが応答できれば200を返す。辞書の読み込み中も200(ホスティング先の起動確認用)。
API仕様書には載せない(docs/functional-design.md「HealthRouter」)。
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def get_health() -> dict[str, str]:
    """起動確認に200を返す。変換が混んでいても詰まらないよう非同期関数にする。"""
    return {"status": "ok"}
