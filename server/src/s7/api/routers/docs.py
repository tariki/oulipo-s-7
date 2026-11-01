"""GET /api/docs(API仕様書)。

FastAPI が作る Swagger UI の上に、画面と同じ見出しの帯(「S+7」とメニュー)を付ける。
API仕様書から変換画面・「このアプリについて」へ移れるようにするため
(docs/functional-design.md「API仕様書(/api/docs)」)。
"""

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

DOCS_PATH = "/api/docs"
OPENAPI_PATH = "/api/openapi.json"
TITLE = "S+7メーカー API"

# 色は web/src/styles/tokens.css、形は web/src/components/SiteHeader.tsx・Wordmark.tsx と同じにする
# (帯は小さく変わることも少ないため、画面と部品を共有する仕組みは作らない)
_HEADER_STYLE = """<style>
body { margin: 0; }
.s7-header { font-family: system-ui, 'Hiragino Sans', 'Noto Sans JP', sans-serif;
  line-height: 1.7; }
.s7-band { color: #ffffff; background: #4f4746; }
.s7-inner { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
  gap: 1rem; max-width: 72rem; margin: 0 auto; padding: 0 1rem; box-sizing: border-box; }
.s7-home { display: block; padding-top: 1rem; color: inherit; line-height: 0; }
.s7-home svg { display: block; width: auto; height: 4.5rem; }
.s7-nav { display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; padding-bottom: 1rem; }
.s7-nav a { display: inline-flex; align-items: center; min-height: 44px; padding: 0 0.5rem;
  color: #ffffff; text-decoration: none; border-left: 6px solid; }
.s7-nav a:hover, .s7-nav a[aria-current='page'] { text-decoration: underline;
  text-underline-offset: 4px; }
.s7-nav .s7-transform { border-left-color: #c9b3ec; }
.s7-nav .s7-about { border-left-color: #e8c46e; }
.s7-nav .s7-api { border-left-color: #b5d27a; }
.s7-band :focus-visible { outline: 2px solid #ffffff; outline-offset: 2px; }
.s7-tagline { margin: 0; padding: 0.5rem 0; font-size: 1.1em; color: #4f4746;
  background: #ffffff; border-bottom: 1px solid #efe8ef; }
.s7-tagline .s7-inner { display: block; }
@media (min-width: 768px) {
  .s7-home svg { height: 8rem; }
  .s7-nav { flex-direction: column; }
}
</style>
"""

_HEADER = """<header class="s7-header">
<div class="s7-band"><div class="s7-inner">
<a href="/" class="s7-home"><svg viewBox="0 0 280 160" role="img" aria-label="S+7メーカー"
 fill="none" stroke="currentColor" stroke-width="28" stroke-linejoin="round">
<path d="M76 40V28H20v52h44v52H8v-12"/>
<path d="M140 52v56M112 80h56"/><path d="M200 28h66l-44 118"/></svg></a>
<nav aria-label="ページ" class="s7-nav">
<a href="/" class="s7-transform">変換する</a>
<a href="/about" class="s7-about">このアプリについて</a>
<a href="/api/docs" class="s7-api" aria-current="page">API</a>
</nav>
</div></div>
<p class="s7-tagline"><span class="s7-inner">
S+7メーカー ― 文章の名詞を、辞書でN個先の名詞に置き換える</span></p>
</header>
"""

router = APIRouter()


@router.get(DOCS_PATH, include_in_schema=False)
async def get_docs() -> HTMLResponse:
    """Swagger UI の HTML に見出しの帯を差し込んで返す。"""
    swagger = get_swagger_ui_html(openapi_url=OPENAPI_PATH, title=TITLE)
    return HTMLResponse(add_header(bytes(swagger.body).decode("utf-8")))


def add_header(html: str) -> str:
    """Swagger UI の HTML の <head> に帯の CSS、<body> の直後に帯を差し込む。

    Raises:
        ValueError: 差し込む位置が見つからない(FastAPI の更新で HTML の形が変わった)。
    """
    for marker in ("</head>", "<body>"):
        if html.count(marker) != 1:
            raise ValueError(f"Swagger UI の HTML に {marker} が1つではありません")
    with_style = html.replace("</head>", _HEADER_STYLE + "</head>")
    return with_style.replace("<body>", "<body>\n" + _HEADER)
