# リポジトリ構造定義書 (Repository Structure Document)

> 対象: `docs/product-requirements.md`、`docs/functional-design.md`、`docs/architecture.md`(2026-10-24)
> 1つのリポジトリに、サーバー(Python)、辞書ビルダー(Python)、画面(TypeScript)を置く。
> 2026-10-25: リポジトリ構造定義書のレビュー(3.4/5)の指摘を反映。`Morpheme` を `domain/` に移し、実行コマンドを `uv run --directory server` に統一し、Dockerfileの各ステージの入力を網羅した。標準の文章を `data/standard-texts/` に移した。

## プロジェクト構造

```
oulipo-s-7/
├── server/                    # Python: APIサーバーと辞書ビルダー(uvの1プロジェクト)
│   ├── pyproject.toml         # 依存関係と、Ruff・mypy・pytest・import-linterの設定
│   ├── uv.lock
│   ├── src/
│   │   ├── s7/                # 実行時のサーバー(コンテナに入る)
│   │   └── s7builder/         # 辞書ビルダー(コンテナに入らない)
│   └── tests/                 # Pythonのテスト
├── web/                       # TypeScript: 画面(ビルドして静的ファイルにする)
│   ├── package.json
│   ├── package-lock.json
│   ├── src/
│   └── tests/                 # 画面のユニットテストとE2Eテスト
├── data/                      # 辞書の元データ・ビルド結果・ビルドの報告・標準の文章
├── licenses/                  # 辞書・ライブラリのライセンス文
├── scripts/                   # 開発・ビルド用のスクリプト
├── tools/
│   └── analysis/              # 辞書データの計測スクリプト(architecture.mdの検証結果)
├── deploy/                    # ホスティング先の設定(ホスティング先の決定後に作る。候補: Cloud Run)
├── .github/                   # GitHub Actions、Dependabot、テンプレート
├── .devcontainer/             # 開発環境(Dev Container)
├── docs/                      # 永続ドキュメント
├── .steering/                 # 作業単位のドキュメント(Git管理外)
├── .claude/                   # Claude Codeの設定
├── Dockerfile                 # マルチステージビルド(画面・辞書・実行用)
├── .dockerignore
├── .env.example               # 実行時の設定(環境変数)の見本。既定値で動くため任意
├── .gitignore
├── CLAUDE.md
└── README.md                  # 概要、セットアップ手順(開発ガイドラインへのリンク)、ライセンスとクレジット
```

**`server/` と `web/` に分ける理由**:
- 言語ごとに依存関係の管理(uv / npm)とツール(Ruff・mypy・pytest / ESLint・Vitest)が独立し、設定が混ざらない
- サーバーと辞書ビルダーは、照合規則や辞書の形式を共有するため同じPythonプロジェクトに置く。ただしパッケージを `s7` と `s7builder` に分け、実行用のイメージに辞書ビルダーを入れない

## ディレクトリ詳細

### server/src/s7/ (実行時のサーバー)

アーキテクチャ設計書のレイヤー構造をそのままディレクトリにする。

```
server/src/s7/
├── __init__.py
├── app.py                         # FastAPIアプリの組み立て(依存の生成、ミドルウェアの登録順、ルーター・静的ファイルの登録)
├── config.py                      # 環境変数から読む設定(一覧はarchitecture.md「環境変数」。利用制限の値はコードで持つ)
├── logging_config.py              # 構造化ログの設定と、本文を除外するログ出力関数(log_request、log_error など)
├── api/                           # APIレイヤー
│   ├── routers/
│   │   ├── transform.py           # POST /api/v1/transform
│   │   ├── senses.py              # GET /api/v1/senses?lemma=... [P1: F8]
│   │   ├── meta.py                # GET /api/v1/meta
│   │   ├── events.py              # POST /api/v1/events(解析用)
│   │   └── health.py              # GET /healthz
│   ├── schemas/                   # Pydanticのリクエスト・レスポンスの型(キー名はcamelCase)
│   │   ├── base.py                # CamelModel(キー名をcamelCaseに変換する共通の基底クラス)
│   │   ├── transform.py
│   │   ├── senses.py
│   │   ├── meta.py
│   │   ├── events.py
│   │   └── errors.py
│   ├── middleware/
│   │   ├── security_headers.py    # CSP・HSTSなどのヘッダーと、パスごとの Cache-Control(architecture.md「HTTPヘッダー」)
│   │   ├── request_logging.py     # /api/v1/* の呼び出しごとに kind=request のログを1行出す(errorCode を含む)
│   │   ├── body_size_limit.py     # 1MBを超える本文を413で断る
│   │   ├── startup_gate.py        # 辞書の読み込み中は503を返す
│   │   ├── internal_error.py      # 想定外の例外を500にする(自前のミドルウェアの最も内側)
│   │   └── rate_limiter.py        # RateLimiter。回数はミドルウェア、文字数は依存関数(transform_char_limit)で判定する
│   ├── static_files.py            # web/dist の配信。/ と /about は index.html を返す。/api/* は静的配信に回さない
│   ├── openapi_description.py     # API仕様書(/api/docs)の全体の説明(入力の型、エラーコード、利用制限、互換性の方針)
│   ├── error_handlers.py          # ErrorHandler(DomainError・検証エラーをエラーレスポンスに変換)
│   └── dependencies.py            # ルーターに渡すサービスの取得と、文字数の利用制限(FastAPIのDepends)
├── services/                      # サービスレイヤー
│   ├── transform_service.py       # TransformService(同時実行を2つに制限するセマフォを持つ)
│   ├── noun_extractor.py          # NounExtractor(品詞の判定、最長一致、見出し語の引き当て)
│   ├── text_chunker.py            # 長文をSudachiに渡せる長さ(40,000バイト以下)に分ける関数
│   ├── formal_nouns.py            # 形式名詞の除外リスト(唯一の正)
│   ├── shifter.py                 # 2つのShifterで共有するN個先の計算(shift_index)
│   ├── gojuon_shifter.py          # GojuonShifter
│   ├── concept_shifter.py         # ConceptShifter
│   ├── sense_selector.py          # SenseSelector
│   ├── sense_service.py           # SenseService(語義の一覧。SenseRouter用)[P1: F8]
│   ├── meta_service.py            # MetaService(辞書のメタ情報と上限値。MetaRouter用)
│   └── gojuon_collation.py        # 五十音順の照合規則の関数(辞書ビルダーと共有)
├── repositories/                  # データレイヤー
│   ├── dictionary_repository.py   # DictionaryRepository(起動時に読み込み、メモリ上で引く)
│   └── dictionary_schema.py       # 変換用辞書のテーブル定義(辞書ビルダーと共有)
├── adapters/                      # 外部ライブラリの境界
│   ├── tokenizer.py               # Tokenizerインターフェース(Protocol)
│   └── sudachi_tokenizer.py       # Sudachiによる実装
└── domain/                        # レイヤーをまたいで使う型(他に依存しない)
    ├── dictionary.py              # Lemma, Synset, SiblingGroup, Sense, DictionaryMeta
    ├── text.py                    # Morpheme(形態素。Tokenizerが返し、Nounが持つ)
    ├── limits.py                  # 入力の上限と利用制限の値(APIのスキーマ、MetaService、RateLimiterで共有)
    ├── transform.py               # Mode, NounStatus, Noun, RawSegment, GojuonRoute, ConceptRoute, GojuonShift, ConceptShift,
    │                              # SenseChoice, ConceptShiftResult, NounResult, TransformResultMeta, TransformResult
    └── errors.py                  # DomainErrorとその派生
```

- 各ディレクトリに `__init__.py` を置き、**中身は空にする**(再公開をしない)。辞書ビルダーが `s7.services.gojuon_collation` を取り込むときに、他のサービスまで読み込まないようにするため
- 機能設計書の中間の型と変換結果の型は、すべて `domain/transform.py` に置く。サービスどうしが型のためだけに互いを取り込まないようにするため

#### api/

**役割**: HTTPの入出力、入力検証、利用制限、エラー形式の統一、ログ、静的ファイルの配信

**命名規則**:
- ルーターはURLの資源名で `routers/[資源名].py`(例: `senses.py`)
- スキーマは対応するルーターと同じファイル名にする(`routers/transform.py` ↔ `schemas/transform.py`)

**ミドルウェアの登録**: `app.py` が、機能設計書「ミドルウェアと処理の順番」の順に登録する。CORS(Starletteの `CORSMiddleware`)とgzip(`GZipMiddleware`)は自前のファイルを作らず、`app.py` で設定して登録する

**依存関係**:
- 依存可能: `services/`、`domain/`、`config.py`、`logging_config.py`
- 依存禁止: `repositories/`、`adapters/`(直接呼ばない。組み立ては `app.py` が行う)

#### services/

**役割**: 変換のロジック(機能設計書のアルゴリズム)

**命名規則**:
- クラスを持つモジュールは1クラス1モジュール。モジュール名はクラス名のsnake_case(`ConceptShifter` → `concept_shifter.py`)
- クラスを持たないモジュール(関数や定数だけ)は、内容を表す名詞のsnake_case(`gojuon_collation.py`、`formal_nouns.py`、`text_chunker.py`)

**依存関係**:
- 依存可能: `domain/`、`repositories/`、`adapters/tokenizer.py`(インターフェースのみ)
- 依存禁止: `api/`、FastAPI・Starlette、`adapters/sudachi_tokenizer.py`、`config.py`、`logging_config.py`(設定値は `app.py` が引数で渡す)

#### repositories/

**役割**: 変換用辞書(SQLite)を読み込み、メモリ上の索引から引く

**依存関係**:
- 依存可能: `domain/`
- 依存禁止: `api/`、`services/`、`adapters/`、`config.py`、`logging_config.py`

#### adapters/

**役割**: Sudachiを `Tokenizer` インターフェースで包む。テストでは偽物の `Tokenizer`(`tests/fixtures/`)に差し替える

**依存関係**:
- 依存可能: `domain/`(`Morpheme` を返すため)、SudachiPy
- 依存禁止: `api/`、`services/`、`repositories/`、`config.py`、`logging_config.py`

#### domain/

**役割**: エンティティ(`dataclass(frozen=True, slots=True)`)、形態素、変換結果の型、例外。どのレイヤーからも使う

**依存関係**:
- 依存可能: Pythonの標準ライブラリのみ
- 依存禁止: `s7` の他のすべてのディレクトリとファイル、外部ライブラリ

#### app.py、config.py、logging_config.py

- `app.py`: 依存関係を組み立てる唯一の場所。`DictionaryRepository`、`SudachiTokenizer`、各サービスをここで生成し、ルーターへ渡す。**このファイルだけは全レイヤーに依存してよい**
- `config.py`・`logging_config.py`: 標準ライブラリだけに依存する。参照してよいのは `app.py` と `api/` だけ(`services/` 以下には値を引数で渡す)。辞書ビルダーは `logging_config.py` を使ってよい
- `config.py` の既定のパス(`data/build/s7dict.sqlite`、`web/dist`)は、**リポジトリ直下を基準に解決する**(`Path(__file__)` からリポジトリ直下を求める)。どのディレクトリから起動しても同じファイルを指すようにするため。コンテナでは、Dockerfileの `ENV` で絶対パスを設定する

### server/src/s7builder/ (辞書ビルダー)

```
server/src/s7builder/
├── __init__.py
├── __main__.py                # コマンドの入口: python -m s7builder build ... / python -m s7builder quality ...
├── version.py                 # DICTIONARY_VERSION(例: "2026.10.0")
├── dictionary_builder.py      # DictionaryBuilder(下の処理を順に呼ぶ)
├── wordnet_reader.py          # WordNetReader
├── lemma_filter.py            # LemmaFilter(置換先から除外する語のリストを適用)
├── reading_assigner.py        # ReadingAssigner
├── sibling_indexer.py         # SiblingIndexer
├── sense_ranker.py            # SenseRanker
├── errors.py                  # BuildError(辞書のビルドの失敗)
├── dictionary_writer.py       # s7dict.sqliteへの書き込み
├── build_report.py            # ビルドの報告(件数、除外した語の数、読みの決め方ごとの数)
└── quality_report.py          # 品質の報告(data/standard-texts/ の3本での両モードの置換率。QualityReporter)
```

**依存関係**:
- 依存可能: `s7.domain`、`s7.services.gojuon_collation`、`s7.services.formal_nouns`、`s7.repositories.dictionary_schema`、`s7.adapters`、`s7.logging_config`
- 例外: `quality_report.py` だけは、変換処理を動かすため `s7.services`・`s7.repositories` にも依存してよい(import-linterの設定で、このモジュールだけを許可する)
- 依存禁止: `s7.api`、`s7.app`。また **`s7` から `s7builder` への依存は禁止**(実行用のイメージに `s7builder` を入れないため)
- 辞書ビルダーは `tests/` 以下のファイルを読まない。入力はすべて `data/` と `licenses/` から取る

**辞書のバージョンを上げる条件**(architecture.mdより): 照合規則(`gojuon_collation.py`)、形式名詞の除外リスト(`formal_nouns.py`)、置換先から除外する語のリスト(`data/excluded-lemmas.txt`)、元データのいずれかを変えたとき。`version.py` を更新する

### server/tests/ (Pythonのテスト)

```
server/tests/
├── conftest.py                    # 共通フィクスチャ(小さな変換用辞書のビルド、TestClient、ログの取り込み)
├── fixtures/
│   ├── wnjpn_sample.sql           # 数十語の日本語WordNetのサンプル(SQL文。差分を読めるようにテキストで持つ)
│   ├── sample_wordnet.py          # wnjpn_sample.sql からSQLiteを作る関数と、それに合わせた読み・除外リスト
│   ├── lexicon.py                 # 表記の一覧から見出し語だけの辞書を作る(名詞抽出のテスト用)
│   └── fake_tokenizer.py          # 決まった形態素を返すTokenizer
├── unit/                          # src/と同じ構造
│   ├── s7/
│   │   ├── services/
│   │   │   ├── test_gojuon_collation.py
│   │   │   ├── test_formal_nouns.py        # formal_nouns.py と設計書・用語集の写しの一致
│   │   │   ├── test_noun_extractor.py
│   │   │   ├── test_text_chunker.py
│   │   │   ├── test_transform_service.py
│   │   │   ├── test_gojuon_shifter.py
│   │   │   ├── test_concept_shifter.py
│   │   │   └── test_sense_selector.py
│   │   ├── repositories/
│   │   │   ├── test_dictionary_schema.py      # テーブルの列とエンティティの項目の一致
│   │   │   └── test_dictionary_repository.py  # 整合性の検査
│   │   └── api/
│   │       └── middleware/
│   │           └── test_rate_limiter.py
│   └── s7builder/
│       ├── test_wordnet_reader.py  # 名詞だけを読む、同じ sid の定義文の版、頻度の合計、読めないファイル
│       ├── test_lemma_filter.py
│       ├── test_reading_assigner.py
│       ├── test_sibling_indexer.py
│       ├── test_sense_ranker.py
│       ├── test_dictionary_writer.py  # 外部キーの検査、ファイルの権限
│       └── test_quality_report.py # 置換率の計算(偽物のTokenizerと小さな辞書で)
├── integration/
│   ├── api/                       # TestClientでAPIを呼ぶ(conftest.py: small_repo と WordListTokenizer でサービスを組み立てる)
│   │   ├── test_transform.py      # 正常系、入力の型の厳しさ、segments の連結で元の文章に戻ること
│   │   ├── test_errors.py         # エラーコードの一覧
│   │   ├── test_rate_limit.py     # 回数・文字数の429と Retry-After
│   │   ├── test_cors.py           # 413・429・503の応答にもCORSヘッダーが付くこと、プリフライト
│   │   ├── test_startup_gate.py   # 辞書の読み込み中の503
│   │   ├── test_body_size_limit.py  # 1MBを超える本文の413(Content-Length あり・chunked)。上限ちょうどの本文が通ること
│   │   ├── test_static_files.py   # / と /about が index.html を返すこと、Cache-Control
│   │   ├── test_logging_format.py # ログの各行の項目と型、本文を含まないこと
│   │   ├── test_determinism.py    # 同じ入力を2回送って同じ結果になること
│   │   ├── test_senses_and_meta.py  # 語義の一覧、メタ情報、API仕様書の説明
│   │   ├── test_events.py         # アクセス解析のイベントの検証とログ、起動中も受け付けること
│   │   └── test_security_headers.py  # セキュリティヘッダー、Cache-Control、gzip
│   ├── builder/
│   │   ├── test_build_sample.py   # wnjpn_sample.sqlからビルドし、件数・並び順・兄弟グループと、2回ビルドの一致を確かめる
│   │   └── test_main.py           # python -m s7builder の終了コード、報告のファイル、既定のパス
│   └── sudachi/                   # 本物のSudachiを使う(マーカー: sudachi)
│       ├── test_sudachi_tokenizer.py  # モードA・C、読み、未知語、記号の仮の読み「キゴウ」
│       ├── test_sudachi_pos.py    # 品詞の扱い(接尾辞・数詞・固有名詞の品詞の値)
│       └── test_sudachi_limits.py # 入力の上限(49,149バイト)
├── snapshot/                      # 本物の変換用辞書が必要(mainへのマージ時のみ実行)
│   ├── expected/                  # [テキスト名].[mode].json
│   └── test_snapshot.py           # data/standard-texts/ の文章を変換して比べる
└── performance/
    └── test_transform_50000.py    # 50,000文字で1秒以内
```

- この一覧は例であり、網羅すべき項目は機能設計書「テスト戦略」とarchitecture.md「テスト戦略」に従う。新しい項目は、上の分け方に沿ってファイルを足す

**命名規則**:
- ファイル: `test_[テスト対象のモジュール名].py`(pytestの規約)
- ユニットテストは `src/` と同じ階層に置く(`src/s7/services/concept_shifter.py` → `tests/unit/s7/services/test_concept_shifter.py`)
- 統合テストは機能単位で `test_[機能].py`

**テストの取り込み方**: `server/pyproject.toml` のpytestの設定に `addopts = ["--import-mode=importlib"]` を書き、`tests/` 以下には `__init__.py` を置かない。`tests/unit/s7/` が本物の `s7` パッケージを隠したり、同じ名前のテストファイルが衝突したりしないようにするため

**実行の区別**: pytestのマーカーで分ける

| マーカー | 対象 | プルリクエストのCI | mainへのマージ |
|----------|------|-------------------|----------------|
| (なし) | ユニット・統合(小さな辞書) | 実行 | 実行 |
| `sudachi` | 本物のSudachiを使う(SudachiDict-coreは依存関係に入っているため、本物の辞書のビルドは不要) | 実行 | 実行 |
| `snapshot`、`performance` | 本物の変換用辞書が必要 | 除外 | 実行 |

### web/ (画面)

```
web/
├── package.json
├── package-lock.json
├── index.html
├── vite.config.ts                 # 開発時は /api をサーバーへ中継する。web/ の外を読むため server.fs.allow に '..' を加える
├── vitest.config.ts
├── playwright.config.ts           # projects: PC幅(Chromium、WebKit)とスマートフォン幅360px
├── tsconfig.json
├── eslint.config.js               # ディレクトリ間の依存のルール(下の「画面の依存」)もここに書く
├── .prettierrc
├── public/                        # そのまま配信するファイル(favicon など)
├── src/
│   ├── main.tsx                   # 入口
│   ├── App.tsx                    # ルーティング(/、/about)
│   ├── pages/
│   │   ├── TransformPage.tsx      # 変換画面。フックと部品をつなぎ、解析のイベントを送る
│   │   └── AboutPage.tsx          # このアプリについて(機能設計書「『このアプリについて』の構成」)
│   ├── hooks/
│   │   ├── useServerReadiness.ts  # 準備中の確認(checking・starting)、meta の再試行、20秒の上限
│   │   └── useTransform.ts        # TransformState、保持した変換操作と破棄、503後の再試行、除外と語義の指定
│   ├── components/
│   │   ├── SkipLink.tsx           # 結果へのスキップリンク
│   │   ├── TextInput.tsx
│   │   ├── TextInput.module.css
│   │   ├── ModeSelector.tsx
│   │   ├── NInput.tsx             # F5
│   │   ├── TransformButton.tsx
│   │   ├── StatusBanner.tsx       # 「準備中です」、時間切れ、エラーの表示
│   │   ├── ResultView.tsx
│   │   ├── ParagraphView.tsx      # 段落1つ(memo。2,000文字を超える段落は分けて描画)
│   │   ├── NounToken.tsx
│   │   ├── Legend.tsx             # 語の表示の凡例
│   │   ├── RoutePanel.tsx         # [P1: F6]
│   │   ├── SensePicker.tsx        # [P1: F8]
│   │   └── CopyButton.tsx
│   ├── api/
│   │   ├── ApiClient.ts           # /api/v1/* の呼び出しとエラーの変換。X-S7-Client: web を付ける
│   │   ├── ApiError.ts            # エラーレスポンスを表すクラス
│   │   ├── types.ts               # 生成した型に短い名前を付けて公開する
│   │   └── generated/
│   │       └── schema.d.ts        # OpenAPI仕様から自動生成(手で編集しない)
│   ├── segments/
│   │   ├── joinSegments.ts        # 元の文章・変換後の文章の組み立て
│   │   └── splitParagraphs.ts     # 段落ごとの描画のための分割
│   ├── text/
│   │   └── countChars.ts          # 文字数(コードポイント数)を数える唯一の関数
│   ├── about/
│   │   ├── sources.ts             # licenses/ と data/dictionary-history.md を ?raw で読み込む唯一の場所
│   │   └── parseDictionaryHistory.ts  # 更新履歴を決まった書式から React で描ける形に変換する
│   ├── analytics/
│   │   └── trackEvent.ts          # ApiClient 経由で POST /api/v1/events
│   └── styles/
│       ├── global.css
│       └── tokens.css             # 色・間隔などの変数
└── tests/
    ├── setup.ts                   # Testing Libraryの設定
    ├── unit/                      # src/と同じ構造
    │   ├── components/
    │   │   └── NounToken.test.tsx
    │   ├── hooks/
    │   │   └── useTransform.test.ts   # 保持した操作の破棄、20秒の上限(偽のタイマー)
    │   ├── api/
    │   │   └── ApiClient.test.ts
    │   ├── segments/
    │   │   └── joinSegments.test.ts
    │   └── about/
    │       └── parseDictionaryHistory.test.ts
    └── e2e/                       # Playwright。ユーザーシナリオ単位
        ├── transform-flow.spec.ts
        ├── input-limit.spec.ts
        ├── keyboard.spec.ts
        ├── cold-start.spec.ts     # 準備中(503を返すモック)の表示と、保持した変換の自動実行
        └── performance.spec.ts
```

- テストの一覧はサーバーと同じく例であり、網羅すべき項目は機能設計書「テスト戦略」に従う

#### pages/、hooks/、components/

**役割**:
- `pages/`: URLに対応する画面。フックから状態を受け取り、部品に渡す。解析のイベント(`trackEvent`)を送る
- `hooks/`: 画面の状態と、APIの呼び出しの順序(準備中の再試行、保持した操作など)。Reactのフック
- `components/`: 画面の部品。状態は最小限にし、propsで受け取る。**`ApiClient` と `trackEvent` を呼ばない**。操作はコールバック(`onCopy` など)で返し、イベントは `pages/` が送る(例: コピーの `copy` イベントは `CopyButton` の `onCopy` を受けた `TransformPage` が送る)

**命名規則**:
- コンポーネントはPascalCase、1ファイル1コンポーネント(`NounToken.tsx`)
- スタイルは同じ名前のCSS Modules(`NounToken.module.css`)
- フックは `use` から始まるcamelCase(`useTransform.ts`)

#### api/

**役割**: APIの呼び出しを1か所にまとめる。部品から直接 `fetch` を呼ばない(architecture.md)

- `generated/schema.d.ts` は、サーバーが出力するOpenAPI仕様から `scripts/generate-api-types.sh` で生成する。CIで生成し直し、差分があれば失敗させる(手書きとのずれを防ぐ)
- 他のファイルは `generated/` を直接参照せず、`types.ts` を経由する

#### segments/、text/、about/、analytics/

**役割**: 画面に依存しない処理(関数)。Reactに依存しない

- `about/sources.ts` は `web/` の外(`../licenses/`、`../data/dictionary-history.md`)を `?raw` で読む。そのため `vite.config.ts` の `server.fs.allow` にリポジトリ直下を加える
- 更新履歴はMarkdownの描画ライブラリを使わず、決まった書式(下の「data/」)だけを `parseDictionaryHistory.ts` で読み、Reactの要素として描く(`dangerouslySetInnerHTML` を使わないため)

**命名規則**: 関数ファイルはcamelCaseで動詞から始める(`joinSegments.ts`)。読み込みだけのファイルは内容を表す名詞(`sources.ts`)

### data/ (辞書データと標準の文章)

```
data/
├── wnjpn.db.sha256            # 日本語WordNet 1.1のSHA-256(Git管理)
├── excluded-lemmas.txt        # 置換先から除外する語のリスト(Git管理。1行1語、#以降はコメント)
├── dictionary-history.md      # 辞書バージョンの更新履歴(「このアプリについて」で表示する。Git管理)
├── standard-texts/            # 標準の文章3本(著作権の切れた作品の一節。出典をファイル冒頭に書く。Git管理)
│   └── [テキスト名].txt       # 品質の報告、スナップショットテスト、性能テストで使う
├── source/                    # wnjpn.dbのダウンロード先(Git管理外)
│   └── .gitkeep
├── build/                     # s7dict.sqliteの出力先(Git管理外)
│   └── .gitkeep
└── reports/
    ├── build-report.json      # ビルドの報告(Git管理。辞書を変えたときの影響を差分で確かめる)
    ├── quality-report.json    # 品質の報告(標準の文章3本での置換率。Git管理)
    └── quality-baseline.json  # 置換率の基準値(最初の値。手で更新する)
```

- `wnjpn.db`(約200MB)と `s7dict.sqlite` はリポジトリに入れない
- `build-report.json` と `quality-report.json` は辞書を作り直したら必ず更新してコミットする
- `dictionary-history.md` は辞書のバージョンを上げるときに追記する。書式は次の形だけにする(見出しと箇条書き以外は使わない)

```markdown
## 2026.10.0(2026-10-24)
- 初版
```

### licenses/ (ライセンス文)

```
licenses/
├── wordnet-ja.txt             # 日本語WordNetのライセンス全文
├── sudachidict-LICENSE.txt
├── sudachidict-NOTICE.txt
├── sudachipy-LICENSE.txt
└── generated/                 # 依存ライブラリのライセンス一覧(scripts/generate-licenses.sh で生成。Git管理)
    ├── python.txt             # 実行時のPythonの依存関係
    └── web.txt                # 画面に含まれるnpmの依存関係
```

- 「このアプリについて」は、ビルド時にここのテキストと `data/dictionary-history.md` を読み込んで表示する(`web/src/about/sources.ts`)
- `generated/` はGit管理する。生成していない状態で画面のビルドやテストが失敗しないようにするため。依存関係を変えたら作り直してコミットし、CIで作り直して差分が無いことを確かめる(APIの型と同じ扱い)
- 辞書ビルダーは `wordnet-ja.txt` を変換用辞書の `meta` テーブルに含める

### scripts/ (開発・ビルド用のスクリプト)

| ファイル | 内容 |
|----------|------|
| `fetch-wordnet.sh` | `wnjpn.db` をダウンロードし(配布元の bond-lab/wnja の v1.1 のリリース。`WORDNET_URL` で変えられる)、`data/wnjpn.db.sha256` で中身を確かめる |
| `build-dictionary.sh` | `s7builder build` と `s7builder quality` を実行し、`data/build/s7dict.sqlite` と2つの報告を作る(`quality` は品質の報告の作業で足す。いまは `build` だけ) |
| `check-reports.sh` | 2つの報告(`build-report.json`・`quality-report.json`)を作り直し、コミット済みのものと一致するかを確かめる(CIで使う) |
| `export-openapi.py` | サーバーのOpenAPI仕様をJSONで出力する(サーバーを起動せずに) |
| `generate-api-types.sh` | `export-openapi.py` の出力から `web/src/api/generated/schema.d.ts` を作る |
| `generate-licenses.sh` | Python(実行時の依存関係のみ)とnpm(画面に含まれる依存関係のみ)のライセンス一覧を `licenses/generated/` に作る。使うツールは実装時に決め、architecture.mdの「開発ツール」に加える |
| `dev.sh` | 開発時にサーバー(Uvicorn)と画面(Viteの開発サーバー)を同時に起動する |
| `check.sh` | リント、整形の確認、型チェック、依存の向きの検査、ユニット・統合テストとカバレッジ、画面のビルド、ShellCheckをまとめて実行する(内容は開発ガイドライン「手元で確かめることとCI」) |

**命名規則**: Pythonのファイルも含めてkebab-case(取り込まずにコマンドとして実行するだけのため)

**実行の決まり**:
- どのスクリプトも、Dev Containerのリポジトリ直下から実行できるようにする
- Pythonのツールは `uv run --directory server ...` で実行する。`--directory` は作業ディレクトリを `server/` に移すため、pytest・mypy・Ruff・import-linterが `server/pyproject.toml` の設定を読む(`--project` は作業ディレクトリを変えないため使わない)
- 画面のツールは `npm --prefix web ...` で実行する

### tools/analysis/ (計測スクリプト)

- architecture.mdの「設計前の検証結果」の各項目を計測するスクリプトを置く
- 実行時のサーバー・辞書ビルダーからは参照しない。`uv run --directory server python ../tools/analysis/[スクリプト名].py` で実行する
- ファイル名はsnake_case(例: `measure_reading_coverage.py`)
- いまあるもの: `measure_reading_coverage.py`(読みの付与率と決まらない理由の内訳)、`measure_sibling_groups.py`(兄弟グループの大きさ、上位語が複数ある概念)

### deploy/ と .github/

```
deploy/                        # ホスティング先の決定後に作る
└── cloudrun/
    └── service.yaml           # 例: Cloud Runにした場合の設定(台数、メモリ、同時リクエスト数、タイムアウト)

.github/
├── workflows/
│   ├── ci.yml                 # プルリクエスト: リント、型チェック、依存の向きの検査、ユニット・統合テスト(sudachiを含む)、脆弱性の検査、画面のビルド、APIの型とライセンス一覧の差分確認。辞書に関わるファイルを変えたときだけ辞書ビルド・報告の一致・スナップショットも
│   ├── pr-title.yml           # プルリクエストのタイトルの形式(タイトルの編集でも動く。ci.yml を走り直させないため分ける)
│   └── main.yml               # mainへのマージ: ci.yml の内容に加えて、辞書ビルド、報告の一致の確認、スナップショット、性能、E2E(内容はarchitecture.md「CI/CD」)
├── pull_request_template.md   # 内容は開発ガイドラインの「プルリクエスト」
├── ISSUE_TEMPLATE/
│   └── excluded-word-report.yml  # 不適切な語の報告用(PRDの「除外リストの公開前の完了条件」)
└── dependabot.yml             # uv・npm・Docker(ベースイメージ)・GitHub Actions。週1回、groupsでまとめる。SudachiPy・SudachiDictは対象外にする
```

- コンテナのビルドとデプロイは、ホスティング先の決定後に `deploy.yml` として加える(`main.yml` の成功を条件にする)

### Dockerfile

architecture.mdのマルチステージビルドに対応する。リポジトリ直下をビルドの起点にする(`web/` と `server/` の両方を使うため)。

| ステージ | 取り込むもの | すること | 出力 |
|----------|--------------|----------|------|
| 1. 画面(node:24) | `web/`(`node_modules` を除く)、`licenses/`(`generated/` を含む)、`data/dictionary-history.md` | `npm ci`、`npm run build` | `web/dist/` |
| 2. 辞書(python:3.13) | `server/pyproject.toml`、`server/uv.lock`、`server/src/`、`data/wnjpn.db.sha256`、`data/excluded-lemmas.txt`、`licenses/wordnet-ja.txt`、`scripts/fetch-wordnet.sh` | `uv sync --frozen --no-dev`、`fetch-wordnet.sh`、`python -m s7builder build`(品質の報告は作らない。CIの `main.yml` で作る) | `s7dict.sqlite` |
| 3. 実行用(python:3.13-slim) | `server/pyproject.toml`、`server/uv.lock`、`server/src/s7/`、ステージ1・2の出力 | `uv sync --frozen --no-dev --no-install-project`(SudachiPy・SudachiDict-core・FastAPIなどの依存関係だけを入れる)。`s7/` だけをコピーし、`PYTHONPATH` で読み込む | 実行用イメージ |

- 実行用ステージには `s7builder/`、`tests/`、`wnjpn.db`、Node.js、開発用の依存関係を入れない。辞書ビルダーはパッケージとして入れず、ソースもコピーしない
- 実行用ステージでは `S7_DICTIONARY_PATH`・`S7_STATIC_DIR` を `ENV` で絶対パスにする
- `.dockerignore` の内容は「除外設定」の1か所にまとめる

### docs/ (ドキュメントディレクトリ)

**配置ドキュメント**:
- `product-requirements.md`: プロダクト要求定義書
- `functional-design.md`: 機能設計書
- `architecture.md`: アーキテクチャ設計書
- `repository-structure.md`: リポジトリ構造定義書(本ドキュメント)
- `development-guidelines.md`: 開発ガイドライン
- `glossary.md`: 用語集
- `ideas/`: 壁打ち・調査メモ(下書き)

## ファイル配置規則

### ソースファイル

| ファイル種別 | 配置先 | 命名規則 | 例 |
|------------|--------|---------|-----|
| APIルーター | `server/src/s7/api/routers/` | snake_case(資源名) | `transform.py` |
| Pydanticスキーマ | `server/src/s7/api/schemas/` | ルーターと同名 | `transform.py` |
| ミドルウェア | `server/src/s7/api/middleware/` | snake_case | `rate_limiter.py` |
| サービス | `server/src/s7/services/` | クラス名のsnake_case(クラスが無ければ内容を表す名詞) | `concept_shifter.py`、`gojuon_collation.py` |
| リポジトリ | `server/src/s7/repositories/` | クラス名のsnake_case | `dictionary_repository.py` |
| 外部ライブラリの境界 | `server/src/s7/adapters/` | snake_case | `sudachi_tokenizer.py` |
| エンティティ・型・例外 | `server/src/s7/domain/` | snake_case(内容のまとまり) | `dictionary.py`、`text.py` |
| 辞書ビルダーの処理 | `server/src/s7builder/` | クラス名のsnake_case | `sibling_indexer.py` |
| 画面 | `web/src/pages/` | PascalCase + `Page` | `TransformPage.tsx` |
| フック | `web/src/hooks/` | `use` + PascalCase | `useTransform.ts` |
| 部品 | `web/src/components/` | PascalCase | `NounToken.tsx` |
| 部品のスタイル | `web/src/components/` | 部品名 + `.module.css` | `NounToken.module.css` |
| APIの呼び出し | `web/src/api/` | クラスはPascalCase | `ApiClient.ts` |
| 関数 | `web/src/segments/` など | camelCase、動詞から始める | `joinSegments.ts` |
| 標準の文章 | `data/standard-texts/` | kebab-caseのローマ字 | `wagahai.txt` |

### テストファイル

| テスト種別 | 配置先 | 命名規則 | 例 |
|-----------|--------|---------|-----|
| ユニットテスト(Python) | `server/tests/unit/` | `test_[モジュール名].py` | `test_concept_shifter.py` |
| 統合テスト(Python) | `server/tests/integration/` | `test_[機能].py` | `test_cors.py` |
| スナップショットテスト | `server/tests/snapshot/` | `expected/[テキスト名].[mode].json` | `wagahai.concept.json` |
| 性能テスト(サーバー) | `server/tests/performance/` | `test_[対象].py` | `test_transform_50000.py` |
| ユニットテスト(画面) | `web/tests/unit/` | `[対象].test.ts(x)` | `NounToken.test.tsx` |
| E2Eテスト | `web/tests/e2e/` | `[シナリオ].spec.ts` | `cold-start.spec.ts` |

### 設定ファイル

| ファイル種別 | 配置先 | 備考 |
|------------|--------|------|
| Pythonの依存関係とツール設定 | `server/pyproject.toml` | Ruff、mypy、pytest(マーカー、`--import-mode=importlib`)、import-linterの契約もここに書く。ツールは `server/` を作業ディレクトリにして実行する |
| 画面の依存関係 | `web/package.json` | |
| 画面のツール設定 | `web/` 直下 | `vite.config.ts`、`eslint.config.js` など |
| 実行時の設定 | 環境変数(`S7_` で始める。`PORT` だけは例外) | `server/src/s7/config.py` で読む。一覧はarchitecture.md「環境変数」。`.env` はGit管理外 |
| ホスティング先 | `deploy/[ホスティング先]/` | 決定後に作る |

## 命名規則

### ディレクトリ名

- **レイヤーディレクトリ**: 複数形(`routers/`、`services/`、`repositories/`、`adapters/`、`components/`、`pages/`、`hooks/`)
- **Pythonのパッケージ**: snake_case(Pythonのimportで使えるように、ハイフンは使わない)
- **それ以外**: kebab-case

### ファイル名

| 言語 | 対象 | 規則 | 例 |
|------|------|------|-----|
| Python | モジュール | snake_case(PEP 8) | `noun_extractor.py` |
| Python | クラス | PascalCase(ファイル名ではなくクラス名) | `NounExtractor` |
| Python | `scripts/` のスクリプト | kebab-case(取り込まないため) | `export-openapi.py` |
| TypeScript | Reactコンポーネント、クラス | PascalCase | `ResultView.tsx`、`ApiClient.ts` |
| TypeScript | フック | `use` + PascalCase | `useTransform.ts` |
| TypeScript | 関数 | camelCase | `splitParagraphs.ts` |
| シェルスクリプト | - | kebab-case | `fetch-wordnet.sh` |

Pythonでクラス名とファイル名を合わせないのは、PEP 8とRuffの規約に従うため。代わりに「1クラス1モジュール、モジュール名はクラス名のsnake_case」とする。クラスを持たないモジュールは、内容を表す名詞のsnake_caseにする。

## 依存関係のルール

### サーバーのレイヤー間の依存

```
app.py(組み立て。すべてに依存してよい)
  ↓
api/ ──→ config.py、logging_config.py
  ↓
services/
  ↓            ↓
repositories/  adapters/tokenizer.py(インターフェース)
  ↓            ↓
         domain/
```

- 矢印の向き(上から下)にだけ依存してよい。逆向きは禁止
- `api/` は `services/` と `domain/` に依存してよい。`repositories/` と `adapters/` には依存しない
- `config.py`・`logging_config.py` を参照してよいのは `app.py`・`api/`・`s7builder`(`logging_config.py` のみ)
- `adapters/sudachi_tokenizer.py` を取り込んでよいのは `app.py` と `s7builder` だけ
- `s7builder` → `s7` はよい(取り込める範囲は「server/src/s7builder/」)が、`s7` → `s7builder` は禁止

**CIでの確認**: 上のルールは、import-linter(`lint-imports`)の契約で機械的に確かめる。設定は `server/pyproject.toml` に書く。`layers` 契約(`api` → `services` → `repositories` | `adapters` → `domain`)と、`forbidden` 契約(`s7` → `s7builder`、`services` → `config`・`logging_config`、`s7builder`(`quality_report` を除く)→ `s7.services` の他のモジュール など)を組み合わせる

### 画面の依存

```
pages/ ─┬─→ hooks/ ──────┬──→ api/(ApiClient)
        │                └──→ analytics/ ──→ api/
        ├─→ analytics/
        ├─→ components/ ──→ segments/、text/、api/types.ts(型のみ)
        └─→ about/
```

図は主な向きだけを示す。正確な範囲は下の表に従う。

| ディレクトリ | 依存してよい先 |
|--------------|----------------|
| `pages/` | `hooks/`、`components/`、`analytics/`、`about/`、`segments/`、`text/`、`api/types.ts` |
| `hooks/` | `api/`、`analytics/`、`segments/`、`text/` |
| `components/` | `components/`、`segments/`、`text/`、`api/types.ts`(型のみ) |
| `analytics/` | `api/` |
| `about/`、`segments/`、`text/` | `api/types.ts`(型のみ)。互いには依存しない |
| `api/` | `api/` の中だけ(`generated/` は `types.ts` からだけ参照する) |

- `components/` から `ApiClient`・`trackEvent`・`hooks/` を呼ばない
- どのディレクトリも `pages/` に依存しない

**CIでの確認**: 上の表は、ESLintの `no-restricted-imports` を、ディレクトリごとの設定(`eslint.config.js` の `files` 指定)で表して確かめる

### 循環依存の禁止

- Python: 同じレイヤー内でも循環させない。2つのサービスが互いを必要とする場合は、共通部分を別のサービスに切り出すか、`domain/` の型に依存させる
- TypeScript: ESLintの `import/no-cycle` で検出する

## スケーリング戦略

### 機能の追加

| 追加するもの | 配置方針 |
|--------------|----------|
| 概念版の派生ルール(PRDのP2) | `services/` に `[名前]_shifter.py` を追加し、`shifter.py` の `shift_index` を使う。Shifterが3つ以上になり呼び出し方をそろえる必要が出たら、`shifter.py` に共通のインターフェース(Protocol)を置く。ファイルが10個を超えたら `services/shifters/` にまとめる |
| 他の品詞(V+7など、P2) | 活用の処理は `services/inflection/` を新設する。品詞の判定は `noun_extractor.py` の設定で切り替える |
| 結果の共有URL(P2) | 画面のみの変更。`web/src/share/` を新設する |
| APIのv2 | `api/routers/v2/`、`api/schemas/v2/` を作る。v1のファイルは移動しない |
| サンプル文(P2) | 文章は `web/src/samples/` に置く(サーバーに保存しない) |

### ファイルサイズの管理

- 1ファイル300行以下を推奨。500行を超えたら分割する
- `noun_extractor.py` が大きくなったら、品詞の判定(`pos_filter.py`)と最長一致(`longest_match.py`)に分ける
- `domain/transform.py` が大きくなったら、中間の型(`Noun`、`RawSegment`、各Shift)と結果の型(`NounResult`、`TransformResult` など)に分ける

## 特殊ディレクトリ

### .steering/ (ステアリングファイル)

**役割**: 特定の開発作業における「今回何をするか」を定義

**管理**: Git管理外(`.gitignore` で除外)。作業の記録として手元に残す。設計の決定のうち後から参照するものは、作業の終わりに `docs/` の永続ドキュメントへ反映する

**構造**:
```
.steering/
└── [YYYYMMDD]-[task-name]/
    ├── requirements.md      # 今回の作業の要求内容
    ├── design.md            # 変更内容の設計
    └── tasklist.md          # タスクリスト
```

**命名規則**: `20261024-add-gojuon-shifter` 形式

### .claude/ (Claude Code設定)

```
.claude/
├── commands/                # スラッシュコマンド
├── skills/                  # タスクモード別スキル
├── agents/                  # サブエージェント定義
└── settings.json
```

### .devcontainer/

```
.devcontainer/
├── devcontainer.json        # features(Python 3.13・uv・Node.js 24)、ポート、拡張機能、メモリの要件
└── post-create.sh           # 作成時に1回だけ実行: ShellCheckの導入と依存関係のインストール
```

- `wnjpn.db` からのビルドのため、Dockerに4GB以上のメモリを割り当てる(architecture.md)
- `post-create.sh` もShellCheckの対象にする(`scripts/check.sh`)

## 除外設定

### .gitignore

現在の `.gitignore` に、次を追加する。

```
# Python
.venv/
__pycache__/
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/

# Node.js / 画面
node_modules/
web/dist/
web/coverage/
web/playwright-report/
web/test-results/

# 辞書データ(大きいため。build-report.jsonとsha256はGit管理する)
data/source/*
data/build/*
!data/source/.gitkeep
!data/build/.gitkeep
```

- `uv.lock`、`package-lock.json`、`web/src/api/generated/schema.d.ts`、`licenses/generated/` はGit管理する

### .dockerignore

`.dockerignore` の内容はここだけで定める。`node_modules` などはサブディレクトリにもあるため、`**/` を付ける(付けないとビルドの起点の直下にしか効かない)。

```
**/node_modules
**/.venv
**/__pycache__
**/.mypy_cache
**/.ruff_cache
**/.pytest_cache
web/dist
web/coverage
web/playwright-report
web/test-results
data/source
data/build
docs
.steering
.claude
.devcontainer
.github
.git
.env
```

### ツールの除外

| ツール | 除外対象 |
|--------|----------|
| Ruff、mypy | `.venv/`(`server/` で実行するため `tools/analysis/` は対象外。mypyのstrictは `src/` と `tests/` だけに適用) |
| ESLint、Prettier | `dist/`、`node_modules/`、`src/api/generated/`、`coverage/` |
