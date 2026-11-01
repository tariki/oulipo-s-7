# syntax=docker/dockerfile:1
# アプリ(APIと画面)を1つのイメージにする。設計は docs/architecture.md「コンテナのビルド(マルチステージ)」、
# 各ステージで取り込むファイルは docs/repository-structure.md「Dockerfile」。
# リポジトリ直下をビルドの起点にする: docker build -t s7-maker .
#
# 各ステージはリポジトリと同じ配置(/app/web、/app/server など)にし、スクリプトや辞書ビルダーの
# リポジトリ直下からの相対パスがそのまま使えるようにする。
# ベースイメージはタグとダイジェストで固定し、Dependabot で更新する。

# uv のバイナリを渡すだけのステージ(実行用イメージには入れない)
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

# --- 1. 画面: web/dist を作る ---
FROM node:24.22.1-trixie-slim@sha256:89c5244bc22a9bc3287d89ebc7e49b9cb5bb84cd40e6175ac3421d5a9f68b95a AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
# 「このアプリについて」が ../licenses/ と ../data/dictionary-history.md を読み込む
COPY licenses/ /app/licenses/
COPY data/dictionary-history.md /app/data/dictionary-history.md
COPY web/ ./
RUN npm run build

# --- 2. 辞書: 日本語WordNetを取得し、変換用辞書(s7dict.sqlite)を作る ---
FROM python:3.13.17-trixie@sha256:d5a186865324088bd10d1671801b42297a8fe3f8059143fb22b2e2b776ffa6dd AS dictionary
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app/server
COPY server/pyproject.toml server/uv.lock ./
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev --no-install-project
COPY server/src/ ./src/
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev
COPY data/wnjpn.db.sha256 data/excluded-lemmas.txt /app/data/
COPY licenses/wordnet-ja.txt /app/licenses/wordnet-ja.txt
COPY scripts/fetch-wordnet.sh /app/scripts/fetch-wordnet.sh
RUN /app/scripts/fetch-wordnet.sh
# 品質の報告は作らない(CIの main.yml で作る)。ビルドの報告はイメージの外では使わないため /tmp に出す
RUN .venv/bin/python -m s7builder build \
    --wordnet /app/data/source/wnjpn.db \
    --excluded /app/data/excluded-lemmas.txt \
    --license /app/licenses/wordnet-ja.txt \
    --output /app/data/build/s7dict.sqlite \
    --report /tmp/build-report.json

# --- 3. 実行用 ---
FROM python:3.13.17-slim-trixie@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962 AS runtime
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app/server
# 実行時の依存関係だけを入れる(s7 はパッケージとして入れず、ソースを PYTHONPATH で読む。
# 辞書ビルダー s7builder を実行用イメージに入れないため)
COPY server/pyproject.toml server/uv.lock ./
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv sync --frozen --no-dev --no-install-project
COPY server/src/s7/ ./src/s7/
COPY --from=dictionary /app/data/build/s7dict.sqlite /app/data/s7dict.sqlite
COPY --from=web /app/web/dist/ /app/web/dist/

# ファイルの持ち主は root のまま(実行ユーザーには書き込ませない)
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin s7
USER s7

ENV PATH=/app/server/.venv/bin:$PATH \
    PYTHONPATH=/app/server/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    S7_DICTIONARY_PATH=/app/data/s7dict.sqlite \
    S7_STATIC_DIR=/app/web/dist \
    PORT=8000
EXPOSE 8000

# ホスティング先が渡す PORT で待ち受ける。シェルで PORT を展開し、exec で uvicorn を PID 1 にする
# (停止のシグナル SIGTERM を uvicorn が直接受け取るため)
CMD ["sh", "-c", "exec uvicorn --factory s7.app:create_app --host 0.0.0.0 --port \"$PORT\" --no-access-log"]
