"""サーバーのOpenAPI仕様をJSONで標準出力に出す(サーバーを起動せず、辞書も読み込まない)。

    uv run --directory server python ../scripts/export-openapi.py

画面のAPIの型(web/src/api/generated/schema.d.ts)は、この出力から
scripts/generate-api-types.sh で作る。
"""

import json
import sys

from s7.app import create_app
from s7.config import load_settings


def main() -> None:
    """アプリを組み立て、OpenAPI仕様を出す。

    lifespan を動かさないため、辞書の読み込みは始まらない。
    """
    app = create_app(load_settings({"S7_LOG_LEVEL": "ERROR"}))
    json.dump(app.openapi(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
