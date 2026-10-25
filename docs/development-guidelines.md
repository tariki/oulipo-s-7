# 開発ガイドライン (Development Guidelines)

> 対象: `docs/product-requirements.md`、`docs/functional-design.md`、`docs/architecture.md`、`docs/repository-structure.md`、`docs/glossary.md`、`CLAUDE.md`(2026-10-25)
> サーバーと辞書ビルダーはPython、画面はTypeScript。言語ごとの規約と、両方に共通する規約に分けて書く。
> 2026-10-25: 開発ガイドラインのレビュー(3.25/5)の指摘を反映。ログの責務、依存の向き、手元の確認とCIの分担、ツールの設定、辞書とAPIを変えるときの手順を書き直した。

## 共通の原則

### 1. 決定性を壊さない

PRDの信頼性要件「同じ入力・同じ設定・同じ辞書バージョンなら、常に同じ結果を返す」は、このアプリで最も重要な性質。変換結果に関わるコード(`services/`、`s7builder/`)では次を守る。

```python
# ✅ 良い例: 並び順を明示する(兄弟グループには代表語を持つ概念だけが入るため、representative_lemma_id はNoneにならない)
members = sorted(candidates, key=lambda s: (s.representative_lemma_id, s.id))

# ❌ 悪い例: setの順序に頼る(実行ごとに順序が変わりうる)
members = list({s for s in candidates})
```

- `set` を順に回した結果を、そのまま並び順にしない。必ず `sorted` で順序を決める
- 並び替えのキーにNoneが入りうる値を使うときは、Noneを除く前提を書くか、`(x is None, x)` のようにNoneの位置を決める
- 乱数、現在時刻、環境(ロケール、OS)によって結果が変わる処理を使わない。ビルドの報告と品質の報告にも、ビルドした時刻などの毎回変わる値を入れない(`scripts/check-reports.sh` が一致を確かめるため)
- 文字列の比較は文字コード順(Pythonの `<`)に統一する。ロケールに依存する比較(`locale.strcoll`、`Intl.Collator`)は使わない

**理由**: 一度でも結果が揺れると、F7(除外)とF8(語義の選び直し)の `nounIndex` がずれ、スナップショットテストも意味を失うため。

### 2. 入力文を残さない

入力文と変換結果は、ログ、例外のメッセージ、エラーレスポンス、ファイルのどこにも書かない(PRDのプライバシー要件)。

**ログを出す場所は次の表のものだけ**。それ以外の層はログを出さず、例外か戻り値で伝える。

| 出す場所 | 関数(`s7/logging_config.py`) | 内容 |
|----------|-------------------------------|------|
| `api/middleware/request_logging.py` | `log_request` | `kind = request` の行。`/api/v1/*` の呼び出しごとに1行(機能設計書「ログの形式」の項目) |
| `api/routers/events.py` | `log_event` | `kind = analytics` の行 |
| `api/error_handlers.py` | `log_error` | 500のときの `kind = app`・`ERROR` の行。例外のクラス名と識別子だけ |
| `app.py` | `log_app` | 起動、辞書の読み込み完了などの `kind = app` の行 |
| `api/middleware/rate_limiter.py` | `log_app` | 接続元を取れなかったときの `WARNING`(architecture.md「利用制限」) |

```python
# ✅ 良い例: ミドルウェアだけがリクエストのログを出す。項目は機能設計書「ログの形式」のとおり
log_request(method=request.method, path=request.url.path, status=response.status_code,
            duration_ms=elapsed_ms, client=request.headers.get("x-s7-client"),
            mode=ctx.mode, n=ctx.n, chars=ctx.chars, error_code=ctx.error_code)
# ログでは duration_ms → durationMs、error_code → errorCode のようにcamelCaseで出す

# ❌ 悪い例
logger.info("transform request: %s", req)          # 本文を含むオブジェクトをそのまま出す
log_error(message=str(exc))                         # 例外のメッセージに入力値が入りうる
return JSONResponse({"detail": exc.errors()})       # 検証エラーの input に本文がそのまま入る
```

- `services/`・`repositories/`・`adapters/`・`domain/` はログを出さない(`logging_config.py` に依存しない。`docs/repository-structure.md`「依存関係のルール」)
- `print` と `logging` の直接の使用はRuffで禁止する(`T20`、`TID251`。`logging_config.py` だけを例外にする)
- 例外のメッセージに本文や名詞を入れない。入れてよいのは文字数、`nounIndex`、概念IDなどの数値・識別子だけ。`log_error` も `str(exc)` を出さない
- **検証エラー**: `error_handlers.py` は、Pydanticのエラーの `type` と `loc` だけを使ってエラーコードを決める(下の「入力検証とエラーコード」)。`input`・`msg`・`ctx` は応答にもログにも使わない
- **Uvicornのアクセスログ**: 止める(`access_log=False`)。クエリ文字列(`?lemma=...`)をそのまま出すため。Uvicorn自身のエラーログは `logging_config.py` でJSON形式にそろえる
- ログの形式は `S7_LOG_FORMAT`(`json` / `text`)、出す重要度は `S7_LOG_LEVEL` で切り替える(architecture.md「環境変数」)
- 統合テスト `test_logging_format.py` で、標準出力に出る行がすべて構造化ログの形式であり、本文と見出し語を含まないことを確かめる
- 画面も `console.*` を使わない(ESLintの `no-console` を常にエラーにする)

### 3. 文字数はコードポイントで数える

上限50,000文字は、サーバー・画面ともに**Unicodeのコードポイント数**で数える。

```typescript
// ✅ 良い例: コードポイント数(Pythonの len() と一致する)
const charCount = [...text].length;

// ❌ 悪い例: UTF-16の単位数(絵文字が2文字と数えられ、サーバーとずれる)
const charCount = text.length;
```

文字数を数える処理は画面では `countChars()`(`web/src/text/countChars.ts`)の1か所にまとめる。

### 4. 用語は用語集に合わせる

- コード上の名前は `docs/glossary.md` の英語名に合わせる(例: 見出し語 = `Lemma`、概念 = `Synset`、兄弟グループ = `SiblingGroup`、五十音順S+N = `gojuon`)
- 識別子は英語、コメント・docstring・エラーメッセージ・テスト名の説明は日本語

### 5. 依存の向きを守る

依存してよい向きは `docs/repository-structure.md`「依存関係のルール」が正。要点は次のとおりで、どちらもCIで機械的に確かめる。

| 対象 | 要点 | 検査 |
|------|------|------|
| サーバー | `api/` → `services/` → `repositories/`・`adapters/tokenizer.py` → `domain/`。`app.py` だけが全層に依存してよい。`config.py`・`logging_config.py` は `app.py` と `api/` だけが使う。`s7` → `s7builder` は禁止。`s7builder` のうち `quality_report.py` だけが `s7.services`・`s7.repositories` を使える | import-linter(`server/pyproject.toml` の `[tool.importlinter]`) |
| 画面 | `pages/` → `hooks/`・`components/`・`analytics/`・`about/`。`hooks/` → `api/`・`analytics/`。`components/` は `ApiClient`・`trackEvent`・`hooks/` を使わない。`api/generated/` は `api/types.ts` からだけ | ESLintの `no-restricted-imports`(`web/eslint.config.js` の、ディレクトリごとの `files` 指定) |

- 例外を足すときは、先に `docs/repository-structure.md` を直し、同じプルリクエストで設定(import-linterの契約、ESLintの設定)を直す。設定だけを緩めない

## コーディング規約: Python(server/)

### ツールと設定

設定はすべて `server/pyproject.toml` に書く。ツールは `uv run --directory server ...` で実行する(作業ディレクトリを `server/` にして設定を読ませるため)。

| 項目 | 設定 |
|------|------|
| 整形 | `ruff format`。行の長さ100、ダブルクォート。全角文字は幅2で数えるため、日本語のコメントは1行50文字程度で折り返す |
| リント | `ruff check`。有効にするルール: `E, F, W, I, N, UP, B, SIM, RUF, PT, S, T20, TID, D, C90, PLR` |
| 型チェック | `mypy --strict`(`src/` と `tests/`) |
| 依存関係の検査 | import-linter(`lint-imports`。上の「5. 依存の向きを守る」) |

**Ruffの細かい設定**:

| 設定 | 値 | 理由 |
|------|-----|------|
| `ignore` | `RUF001`、`RUF002`、`RUF003` | 全角の句読点(`。！？（`)や長音を、まぎらわしい文字として報告するため |
| `pydocstyle.convention` | `google` | docstringをGoogleスタイルにそろえる |
| `ignore`(追加) | `D415` | 日本語のdocstringは「。」で終えるため(Googleスタイルの設定では `D400` は対象外) |
| `per-file-ignores` | `tests/**`: `S101`(`assert`)、`D`、`PLR2004` | テストでは `assert` と具体的な値を使い、docstringは任意にする |
| `per-file-ignores` | `src/s7/logging_config.py`: `TID251` | `logging` を使ってよい唯一の場所 |
| `flake8-tidy-imports.banned-api` | `logging` | ログの経路を `logging_config.py` に限るため |
| `mccabe.max-complexity` | 10 | 関数の分岐が多すぎないように |
| `pylint.max-statements` | 30 | 下の「関数設計」の目安を機械的に見る |
| `pylint.max-args` | `self` を除いて5個まで通る値 | 下の「関数設計」。`self` を数えるかは導入時に確かめて決める |

- `scripts/*.py` と `tools/analysis/` は `server/` の外にあるため、上のツールの対象にならない。手で `uv run --directory server ruff check ../scripts ../tools/analysis` を実行して整える(mypyのstrictは求めない)

### 命名規則

```python
# モジュール: snake_case。クラスを持つモジュールは1クラス1モジュールで、モジュール名はクラス名のsnake_case
# concept_shifter.py
# クラスを持たないモジュールは内容を表す名詞: gojuon_collation.py、formal_nouns.py

# クラス: PascalCase、名詞
class ConceptShifter: ...

# 関数・メソッド: snake_case、動詞で始める
def find_lemma(self, surface: str) -> Lemma | None: ...
def compute_sort_key(reading: str) -> str: ...

# 変数: snake_case、名詞
sibling_group = repo.sibling_group(group_id)

# 真偽値: is_ / has_ / should_ で始める
is_wrapped = index + n >= size

# 定数: UPPER_SNAKE_CASE(モジュールの先頭に置く)
MAX_MERGE_MORPHEMES = 8
DEFAULT_N = 7
MAX_CHARS = 50_000

# 非公開: 先頭に _
def _normalize_reading(reading: str) -> str: ...
```

### 型ヒント

- すべての関数の引数と戻り値に型を書く(mypy strictで強制)
- 組み込みの型と `|` を使う。`typing.List`、`Optional` は使わない
- 引数の型は抽象型(`collections.abc` の `Sequence`、`Mapping`)、戻り値は具体型(`list`、`dict`)にする
- 決まった値の集合は `Literal` で表す(`Mode`、`NounStatus`、`ErrorCode`)。APIの値とそのまま比べられ、Pydanticとも相性がよいため。`StrEnum` は使わない

```python
from collections.abc import Mapping
from typing import Literal

Mode = Literal["gojuon", "concept"]

# ✅ 良い例
def transform(self, text: str, mode: Mode, n: int,
              exclusions: frozenset[int] = frozenset(),
              sense_overrides: Mapping[int, str] | None = None) -> TransformResult: ...

# ❌ 悪い例: 変更可能な既定値(呼び出しをまたいで共有される)
def transform(self, text, mode, n, sense_overrides={}): ...
```

### データの型

- エンティティと値は `@dataclass(frozen=True, slots=True)` で定義し、作成後に変更しない(設計書のコード例では `slots=True` を省いているが、実装では付ける)
- HTTPの入出力はPydanticのモデル(`api/schemas/`)、内部のデータは `dataclass`(`domain/`)と分ける。サービスにPydanticのモデルを渡さない

### 入力検証とエラーコード

リクエストのモデルは、機能設計書「入力の型の厳しさ」のとおり型の自動変換をしない。

```python
# api/schemas/transform.py
class TransformRequest(CamelModel):  # キー名をcamelCaseに変換する共通の基底クラス
    model_config = ConfigDict(strict=True, extra="ignore")  # 型を変換しない。知らない項目は無視する(APIの互換性)

    text: str = Field(max_length=MAX_CHARS)
    mode: Mode
    n: int = Field(default=DEFAULT_N, ge=1, le=99)  # strictなので "7"・7.0・true は断る
    exclusions: list[int] = Field(default_factory=list, max_length=MAX_EXCLUSIONS)
    sense_overrides: dict[str, str] = Field(default_factory=dict, max_length=MAX_SENSE_OVERRIDES)

    @field_validator("text")
    @classmethod
    def _check_text(cls, text: str) -> str:
        if text == "" or text.isspace():
            raise PydanticCustomError("text_empty", "text is empty")       # 本文はメッセージに入れない
        if any(0xD800 <= ord(c) <= 0xDFFF for c in text):
            raise PydanticCustomError("lone_surrogate", "text has a lone surrogate")
        return text
```

`error_handlers.py` は、最初の検証エラーの `loc` と `type` からエラーコードを決める。対応表は `error_handlers.py` に1つだけ持つ。

| `loc` | `type` | エラーコード |
|-------|--------|--------------|
| `("body", "text")` | `text_empty`、`missing` | `TEXT_EMPTY` |
| `("body", "text")` | `string_too_long` | `TEXT_TOO_LONG` |
| `("body", "mode")` | どれでも | `INVALID_MODE` |
| `("body", "n")` | どれでも | `INVALID_N` |
| それ以外 | どれでも(`lone_surrogate`、JSONの形式の不正、`exclusions` などの型や個数を含む) | `INVALID_REQUEST` |

- 文字数の比較はPythonの `len()`(コードポイント数)で行われるため、`max_length` で `TEXT_TOO_LONG` を判定してよい
- 対応表のすべての行を `test_errors.py` で確かめる

### 関数設計

- 1つの関数は1つの責務。目安は20行以内、50行を超えたら分割を検討する(Ruffの `max-statements` は30)
- 引数は `self` を除いて5個まで。超えたら `dataclass` にまとめる
- 計算(純粋な関数)と入出力(SQLite、Sudachi)を分ける。照合規則、最長一致、N個先の計算は、辞書もSudachiも使わない純粋な関数として書き、単体でテストする

```python
# ✅ 良い例: 計算を純粋な関数に切り出す
def shift_index(index: int, n: int, size: int) -> tuple[int, bool]:
    """リスト上でN個先の位置と、末尾を超えて先頭に戻ったかを返す。"""
    return (index + n) % size, index + n >= size
```

### エラーハンドリング

例外は3つに分ける。

| 種類 | 基底クラス | 例 | 扱い |
|------|------------|-----|------|
| 予期されるエラー(利用者に伝える) | `DomainError`(`domain/errors.py`) | `LemmaNotFoundError` | `error_handlers.py` が `code` に対応するHTTPステータスで返す |
| 辞書やコードの不備(起きてはいけない) | `DictionaryIntegrityError(Exception)`(`domain/errors.py`) | 親の概念が辞書に無い | 捕まえない。`error_handlers.py` が500(`INTERNAL_ERROR`)にし、`log_error` で記録する |
| 辞書ビルダーの失敗 | `BuildError(Exception)`(`s7builder/`) | 除外リストが無い・空、整合性の検査の失敗 | `__main__.py` が捕まえ、標準エラー出力に理由を書いて終了コード1で終わる |

```python
# domain/errors.py
ErrorCode = Literal["TEXT_EMPTY", "TEXT_TOO_LONG", "INVALID_MODE", "INVALID_N", "INVALID_REQUEST",
                    "LEMMA_NOT_FOUND", "PAYLOAD_TOO_LARGE", "RATE_LIMITED", "SERVICE_STARTING",
                    "INTERNAL_ERROR"]  # 機能設計書「エラーコードの一覧」と同じ

class DomainError(Exception):
    """利用者に伝えるエラーの基底。codeはAPIのエラーコード。"""
    code: ClassVar[ErrorCode]

class LemmaNotFoundError(DomainError):
    code = "LEMMA_NOT_FOUND"

class DictionaryIntegrityError(Exception):
    """変換用辞書の不備。ビルド時の検査で防ぐため、実行時に起きたら500にする。"""
    def __init__(self, synset_id: str) -> None:
        super().__init__(f"概念 {synset_id} が変換用辞書にありません")  # 識別子だけを入れる
        self.synset_id = synset_id
```

```python
# api/error_handlers.py: エラーコードとHTTPステータスの対応はここだけに書く
ERROR_STATUS: Final[Mapping[ErrorCode, int]] = {"LEMMA_NOT_FOUND": 404, "INTERNAL_ERROR": 500, ...}
```

```python
# ✅ 良い例: 辞書に無い語はエラーにせず、結果の状態で表す(機能設計書「6. 変換の組み立て」)
if noun.lemma is None:
    return NounResult(noun_index=noun_index, original=noun.surface, replaced=noun.surface,
                      status="not_in_dictionary", lemma=None, synset_id=None, route=None)

# ❌ 悪い例: 例外を握りつぶす
try:
    lemma = self._repo.lemma(lemma_id)
except Exception:
    return None
```

- `except Exception:` で握りつぶさない。捕まえる場合は型を絞る
- FastAPIの `HTTPException` は `api/` の中でだけ使う

### docstringとコメント

- 公開するクラスと関数には、日本語のdocstring(Googleスタイル)を書く
- 機能設計書のアルゴリズムを実装した箇所には、設計書の節を示す

```python
def merge_longest(run: list[Morpheme], repo: DictionaryRepository) -> list[Noun]:
    """候補区間を、辞書との最長一致で名詞にまとめる。

    機能設計書「1. 名詞抽出と最長一致」ステップ3の実装。

    Args:
        run: 候補区間(名詞(普通・固有・数詞)・接頭辞・名詞的接尾辞が連続する形態素)。長さの上限は無い。
        repo: 連結した表記から見出し語を引き当てる辞書。

    Returns:
        まとめた名詞の列(見出し語つき)。1形態素の普通名詞は辞書に無くても含める。
    """
```

- インラインコメントは「なぜそうするか」を書く。コードを読めば分かることは書かない
- コメントアウトしたコードを残さない
- `TODO` にはGitHubのIssue番号を書く(例: `# TODO(#14): 語義の上書きに対応する`)。`.steering/` はGit管理外なので参照先にしない

### パフォーマンス

- 実行時にSQLiteを引かない。`DictionaryRepository` が起動時にすべて `dict`・`list` へ展開する
- 1語あたりの処理で、リストの線形探索(`list.index`、`in list`)をしない。索引(`dict`)を引く
- Sudachiの辞書は起動時に1回だけ読み込む。変換は同時に2つまでスレッドで動く(architecture.md「同期処理と非同期処理」)ため、Sudachiの `Tokenizer` を複数のスレッドで共有してよいかを実装の初回に確かめる。共有できなければ、スレッドごとに作る(`threading.local`)。決めたら `SudachiTokenizer` のdocstringとarchitecture.mdに書く
- 性能に効く変更は、`tests/performance/` の結果をプルリクエストに書く

### ファイルの大きさ

- 1ファイル300行以下を推奨。500行を超えたら分割する(分け方は `docs/repository-structure.md`「ファイルサイズの管理」)

## コーディング規約: TypeScript(web/)

### ツールと設定

| 項目 | 設定 |
|------|------|
| 整形 | Prettier。インデント2スペース、行の長さ100、シングルクォート、セミコロンあり |
| リント | ESLint(フラット設定)。`typescript-eslint` の `strictTypeChecked`、`eslint-plugin-react`(`react/no-danger` など)、`eslint-plugin-react-hooks`、`eslint-plugin-jsx-a11y`、`eslint-plugin-import-x`(`import-x/no-cycle`)、`no-restricted-imports`(依存の向き)、`no-console`(常にエラー)。`eslint-config-prettier` で整形のルールを外す |
| 型チェック | `tsc -b`(Viteの標準の構成はプロジェクト参照を使うため、`-b` で全体を検査する)。`strict: true`、`noUncheckedIndexedAccess: true` |

**npmのスクリプト**(`web/package.json`):

| スクリプト | 内容 |
|------------|------|
| `dev` | `vite`(開発サーバー) |
| `build` | `tsc -b && vite build` |
| `typecheck` | `tsc -b` |
| `lint` | `eslint .` |
| `format` / `format:check` | `prettier --write .` / `prettier --check .` |
| `test` | `vitest run`(1回だけ実行) |
| `test:watch` | `vitest` |
| `coverage` | `vitest run --coverage` |
| `e2e` | `playwright test` |
| `e2e:install` | `playwright install --with-deps chromium webkit` |

### 命名規則

```typescript
// 変数: camelCase、名詞
const nounSegments = segments.filter(isNounSegment);

// 関数: camelCase、動詞で始める
function joinReplaced(segments: Segment[]): string { ... }

// 真偽値: is / has / should / can で始める
const isTransforming = state.status === 'loading';

// コンポーネント・型・クラス: PascalCase。インターフェースに I 接頭辞は付けない
function NounToken(props: NounTokenProps) { ... }
interface NounTokenProps { segment: NounSegment; onSelect: (nounIndex: number) => void; }

// フック: use + PascalCase
function useTransform(readiness: Readiness): UseTransformResult { ... }

// 定数: UPPER_SNAKE_CASE
const MAX_CHARS = 50_000;

// イベントハンドラー: props は on〜、実装は handle〜
<CopyButton onCopy={handleCopy} />
```

### 型

- `any` は使わない(ESLintでエラー)。型が分からない値は `unknown` にして絞り込む
- APIの型は `src/api/types.ts` からだけ取り込む。手で同じ形の型を書かない
- 状態は、取りうる組み合わせだけを表せるユニオン型にする。`isLoading` と `error` を別々の変数で持たない

```typescript
// hooks/useTransform.ts: 変換画面の状態(用語集「変換画面の状態」)
type TransformState =
  | { status: 'checking' }
  | { status: 'starting' }
  | { status: 'idle'; staleResult?: TransformResponse }
  | { status: 'loading' }
  | { status: 'success'; result: TransformResponse }
  | { status: 'error'; error: ApiError };
```

### 画面の責務の分け方

| 置き場所 | 持つもの | 持たないもの |
|----------|----------|--------------|
| `hooks/useServerReadiness.ts` | 準備中の確認(`GET /api/v1/meta` の再試行、20秒の上限)。結果を `checking`・`starting`・`ready`・`timedOut` で返す | 変換の状態 |
| `hooks/useTransform.ts` | `TransformState`(`useServerReadiness` の結果を `checking`・`starting` として反映する)、保持した変換操作とその破棄、503後の再試行、除外と語義の指定 | 表示 |
| `pages/` | フックと部品をつなぐ。解析のイベント(`trackEvent`)を送る | APIの呼び出しの順序 |
| `components/` | 表示と操作。データはpropsで受け取り、操作はコールバックで返す | `ApiClient`、`trackEvent`、フックの呼び出し |

- 例: コピーの `copy` イベントは、`CopyButton` の `onCopy` を受けた `TransformPage` が送る

### Reactの規約

- 関数コンポーネントとフックだけを使う
- 状態は `useState`・`useReducer` で持つ(状態管理ライブラリは使わない。architecture.md)
- `dangerouslySetInnerHTML` は使わない(`react/no-danger` でエラー)。辞書の更新履歴も `about/parseDictionaryHistory.ts` でReactの要素にする
- 長い結果は段落ごとに `memo` した部品(`ParagraphView`)で描画し、Nやルールを変えても入力欄を再描画しない

### アクセシビリティ

WCAG 2.2 AAを満たすため、実装時に次を守る。

```tsx
// ✅ 良い例: 選べる語はbutton。色以外の手がかり(下線・記号)と、読み上げ用の説明を付ける
<button
  type="button"
  className={styles.replaced}
  aria-describedby={tooltipId}
  onClick={() => onSelect(segment.nounIndex)}
>
  {segment.replaced}
</button>

// ❌ 悪い例: クリックできるspan(キーボードで選べない)、色だけで区別
<span style={{ background: 'yellow' }} onClick={...}>{segment.replaced}</span>
```

- クリックできる要素は `button` か `a` にする。`div`・`span` に `onClick` を付けない(`jsx-a11y` で検出)
- 名詞の6つの状態は、色に加えて下線の種類と記号(「↑」「?」「・」、取り消し線)で区別する(機能設計書「語の表示」)。凡例(`Legend`)を出す
- 結果の語は矢印キーで移動できるようにする(ロービングタブインデックス)。スキップリンク(`SkipLink`)で結果へ飛べるようにする(機能設計書「キーボード操作」)
- フォーカスしている要素は、2px以上の枠で見えるようにする。`outline: none` だけで消さない
- 押せる要素は24×24 CSSピクセル以上にする(WCAG 2.2 の 2.5.8)
- 入力欄には `label` を付ける。文字数の上限超過と準備中の表示は `aria-live` で読み上げる
- 色のコントラストは4.5:1以上(大きな文字は3:1以上)。色は `styles/tokens.css` の変数だけを使う
- E2Eテストで `@axe-core/playwright` を使い、主な画面(入力待ち、結果表示、エラー、このアプリについて)に違反が無いことを確かめる

### エラーハンドリング

- `ApiClient` は、エラーレスポンスと通信の失敗を `ApiError`(`code` を持つ)に変換して投げる
- 画面は `ApiError.code` に応じたメッセージを表示する(機能設計書「エラーの分類」の文言)。どのエラーでも入力欄の文章を消さない
- `catch` した値を表示用の文字列にそのまま使わない(内部の情報が出るため)

```typescript
try {
  const result = await apiClient.transform(request);
  dispatch({ type: 'succeeded', result });
} catch (error) {
  // 想定外の値も含めて ApiError に寄せ、入力は残したままエラー表示に移る
  dispatch({ type: 'failed', error: ApiError.from(error) });
}
```

## シェルスクリプト(scripts/)

- 先頭は `#!/usr/bin/env bash` と `set -euo pipefail`
- リポジトリ直下を `ROOT="$(cd "$(dirname "$0")/.." && pwd)"` で求め、パスはすべて `$ROOT` から組み立てる。どこから実行しても同じ動きにする
- `uv run --directory server` の中ではパスの基準が `server/` になる。ファイルを渡すときは `"$ROOT/data/build/s7dict.sqlite"` のように絶対パスにする
- ShellCheckの警告が無い状態にする(`scripts/check.sh` で実行する)

## APIを変えるときの手順

APIは公開する(PRDのF9)ため、互換性のある変更だけを `/api/v1` で行う。互換性の範囲は機能設計書「APIの互換性」が正。

| 変更 | 扱い |
|------|------|
| レスポンスへの項目の追加、省略できるリクエスト項目の追加、エンドポイントの追加 | `v1` のまま行ってよい |
| 項目の削除・名前の変更・意味の変更 | `v2` で行う |
| 既存のリクエストへの応答で、新しい値(`NounStatus`、エラーコードなど)を返す | `v2` で行う |

1. 機能設計書の「API設計」(型、エンドポイント、エラーコードの一覧)を先に直す。新しい用語があれば用語集も直す
2. `api/schemas/` を直す。エラーコードを足すなら `domain/errors.py` の `ErrorCode` と `error_handlers.py` の対応表も直す
3. `scripts/generate-api-types.sh` を実行し、`web/src/api/generated/schema.d.ts` をコミットする
4. 統合テスト(`tests/integration/api/`)に、新しい入出力とエラーの場合を足す
5. プルリクエストに、上の表のどれに当たるかを書く

ミドルウェアの処理の順番(機能設計書「ミドルウェアと処理の順番」)を変える場合も、先に機能設計書と用語集を直し、`app.py` の登録順と統合テストを合わせる。

## Git運用ルール

作業の進め方の全体(ステアリングファイルによる計画 → 実装 → 検証)は `CLAUDE.md` の「スペック駆動開発の基本原則」に従う。ここでは、その中のブランチとプルリクエストの決まりを書く。

### ブランチ戦略(GitHub Flow)

```
main(常に動く状態。ホスティング先の決定後は、マージするとデプロイされる)
  ├── feature/gojuon-shifter
  ├── fix/rate-limit-header
  └── docs/glossary-update
```

| ブランチ | 用途 |
|----------|------|
| `main` | 本番。直接コミットしない。マージは必ずプルリクエストから |
| `feature/[内容]` | 機能の追加 |
| `fix/[内容]` | 不具合の修正 |
| `refactor/[内容]`、`docs/[内容]`、`chore/[内容]` | それぞれの種類の変更 |
| `dict/[内容]` | 変換用辞書のバージョンが上がる変更(下の「変換用辞書を変えるときの手順」の条件のどれか) |

**Git Flow(`develop` ブランチ)を使わない理由**:
- architecture.mdで「mainへのマージでデプロイ」と決めており、リリースの準備期間を設ける必要が無い
- 開発者が少なく、並行するリリースの管理が要らない

**マージ方針**: squash merge。プルリクエスト1つが `main` のコミット1つになり、**プルリクエストのタイトルがコミットの件名になる**。タイトルは下のコミットメッセージの形式で書き、CIで形式を確かめる

### mainの保護(GitHubの設定)

| 設定 | 値 |
|------|-----|
| プルリクエストを必須にする | はい(直接のpushと強制pushは禁止) |
| 必須のステータスチェック | `ci.yml` のすべてのジョブ |
| マージの方式 | squash mergeだけを許す |
| 必要な承認の数 | 開発者が1人のうちは0(CIが通れば自分でマージしてよい)。2人以上になったら1 |
| マージ前にブランチを最新にする | はい |

- `main.yml`(マージ後)が失敗したら、原因を調べる前に、まずそのプルリクエストを `git revert` するプルリクエストを出して `main` を戻す

### コミットメッセージ

Conventional Commitsに従う。件名は日本語で、50文字程度まで。

```
<type>(<scope>): <件名>

<本文: 何を・なぜ変えたか>

<フッター: Closes #12 など>
```

| type | 用途 |
|------|------|
| `feat` | 機能の追加 |
| `fix` | 不具合の修正 |
| `perf` | 性能の改善 |
| `refactor` | 動作を変えない整理 |
| `test` | テストの追加・修正 |
| `docs` | ドキュメント |
| `build` | 依存関係、Dockerfile |
| `ci` | GitHub Actions |
| `chore` | その他 |

| scope | 対象 |
|-------|------|
| `api` | `s7/api/`、`s7/app.py`、`s7/config.py`、`s7/logging_config.py` |
| `service` | `s7/services/`、`s7/domain/` |
| `repo` | `s7/repositories/`、`s7/adapters/` |
| `builder` | `s7builder/` |
| `dict` | 変換用辞書の内容が変わる変更(辞書のバージョンを上げる) |
| `web` | `web/` |
| `infra` | `deploy/`、`Dockerfile`、`.dockerignore`、`.devcontainer/` |
| `scripts` | `scripts/`、`tools/analysis/` |

- `.github/workflows/` の変更はtypeの `ci` を使い、scopeを付けない
- `data/` と `licenses/` の変更は、変換用辞書の内容が変わるなら `dict`。それ以外(`dictionary-history.md` の誤字、`licenses/generated/` の作り直しなど)はscopeを付けない
- 上のどれにも当たらないもの(`.claude/`、`.github/` のテンプレート、`.gitignore` など)は、typeの `chore` にしてscopeを付けない

**例**:
```
feat(service): 概念版S+Nで兄弟が無いときに階層を上がる

兄弟グループが自分だけの概念は、上位語の兄弟グループで
N個先に進むようにした(機能設計書 アルゴリズム4 ステップ3)。
最上位まで兄弟が無い場合は no_sibling を返す。

Closes #14
```

### 手元で確かめることとCI

| 確かめること | 手元(`scripts/check.sh`) | プルリクエスト(`ci.yml`) | mainへのマージ(`main.yml`) |
|--------------|:------------------------:|:-----------------------:|:--------------------------:|
| Python: `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | ○ | ○ | ○ |
| Python: `pytest`(ユニット・統合・`sudachi`。本物の辞書が不要なもの)とカバレッジ | ○ | ○ | ○ |
| 画面: `lint`、`format:check`、`typecheck`、`test`(カバレッジ)、`build` | ○ | ○ | ○ |
| シェルスクリプト: ShellCheck | ○ | ○ | ○ |
| `pip-audit`、`npm audit` | - | ○ | ○ |
| APIの型とライセンス一覧を作り直して差分が無いこと | - | ○ | ○ |
| プルリクエストのタイトルの形式 | - | ○ | - |
| 本物の辞書のビルド、報告の一致(`scripts/check-reports.sh`)、スナップショット | - | 辞書に関わるファイルを変えたときだけ(下記) | ○ |
| 性能(サーバー)、E2E | - | - | ○ |
| コンテナのビルドとデプロイ | - | - | 別のワークフロー `deploy.yml`(ホスティング先の決定後に作る) |

- **辞書に関わるファイル**: `server/src/s7builder/**`、`server/src/s7/services/gojuon_collation.py`、`server/src/s7/services/formal_nouns.py`、`server/uv.lock`、`data/excluded-lemmas.txt`、`data/wnjpn.db.sha256`、`data/standard-texts/**`。これらを変えたプルリクエストでは、`ci.yml` が `paths` の条件で辞書のビルドと報告の一致・スナップショットも実行する。辞書の更新忘れをマージ前に見つけるため
- 依存関係を変えたら `scripts/generate-licenses.sh`、APIを変えたら `scripts/generate-api-types.sh` を手元で実行し、結果をコミットする(CIは作り直して差分を確かめるだけ)

### プルリクエスト

**作成前のチェック**:
- [ ] `scripts/check.sh` が通る
- [ ] APIを変えた場合: `scripts/generate-api-types.sh` の結果をコミットした
- [ ] 依存関係を変えた場合: `scripts/generate-licenses.sh` の結果をコミットした
- [ ] 辞書に関わるファイルを変えた場合: 「変換用辞書を変えるときの手順」を済ませた

**大きさの目安**: 変更は300行以内、ファイル10個以内。超える場合は分ける(生成ファイルとスナップショットは数えない)

**テンプレート**(`.github/pull_request_template.md`):

```markdown
## 何を変えたか
[簡潔な説明。ステアリングファイルの要点(要求と設計の判断)もここに書く。.steering/ はGit管理外のため]

## なぜ変えたか
[背景]

## 確認したこと
- [ ] ユニットテスト / 統合テストを追加・更新した
- [ ] 画面を変えた場合: PC幅とスマートフォン幅(360px)、キーボード操作で確かめた
- [ ] 性能に効く変更の場合: tests/performance/ の結果を下に書いた

## 変換結果への影響
- [ ] 変換結果は変わらない
- [ ] 変換結果が変わる → 辞書のバージョンを上げ、build-report.json・quality-report.json・スナップショット・dictionary-history.md を更新し、差分を下に書いた

## ドキュメントと生成物
- [ ] docs/ の更新は不要 / 更新した(ファイル名: )
- [ ] 依存関係を追加した場合: ライセンス(下の「依存関係の更新」の許可リスト)を確かめ、licenses/generated/ を作り直した
- [ ] APIを変えた場合: 互換性の扱い(「APIを変えるときの手順」の表)を書いた

## レビューしてほしい点
[特に見てほしい箇所]
```

### レビュー

**観点**:

| 観点 | 確認すること |
|------|-------------|
| 機能 | PRD・機能設計書の受け入れ条件を満たすか。境界(N=1/99、50,000文字、空の入力、末尾からの循環) |
| テスト | 変更に対応するテストがあるか。機能設計書「テスト戦略」の項目が増えていれば、その分のテストがあるか |
| 決定性 | 並び順が明示されているか。`set` や環境に依存していないか |
| プライバシー | 本文がログ・例外・エラーレスポンス・外部へ出ていないか |
| 依存の向き | 「5. 依存の向きを守る」に従っているか(CIでも確認) |
| APIの互換性 | 「APIを変えるときの手順」の表で `v1` のまま行ってよい変更か |
| ドキュメント | 設計を変えた場合、`docs/` を同じプルリクエストで直しているか |
| アクセシビリティ | キーボードで操作できるか、色以外の手がかりがあるか |
| 性能 | 1語あたりの処理に線形探索や辞書の読み込みが無いか |

**進め方**: レビューを頼まれたら、2営業日以内に最初のコメントを返す(開発者が2人以上になってから適用する)

**コメントの優先度**: `[必須]`(直さないとマージしない)、`[推奨]`、`[提案]`、`[質問]` を先頭に付ける

```markdown
✅ [必須] ここで set を回した順に兄弟を並べているため、実行ごとに順序が変わります。
   代表語の Lemma.id → 概念ID で sorted してください(機能設計書 アルゴリズム4)。

❌ この並べ方はダメです。
```

## テスト戦略

網羅すべき項目は機能設計書「テスト戦略」とarchitecture.md「テスト戦略」が正。ここでは道具と書き方を決める。

### テストの種類と目標

| 種類 | ツール | 対象 | 目標 |
|------|--------|------|------|
| ユニット(Python) | pytest | 照合規則、読みの決定、最長一致、品詞の判定、長文の分割、各Shifter、語義の選択、変換の組み立て、利用制限、辞書ビルダーの各処理、品質の報告 | 下の「カバレッジ」 |
| ユニット(画面) | Vitest + Testing Library | `components/`、`hooks/`(偽のタイマーで20秒の上限など)、`api/`、`segments/`、`text/`、`about/` | 下の「カバレッジ」 |
| 統合 | pytest + `TestClient` | `tests/integration/api/` の各ファイル(入出力、エラーコード、利用制限、CORS、準備中の503、413、静的配信、ログの形式、決定性)と、小さな辞書のビルド | 機能設計書「統合テスト」の全項目 |
| 本物のSudachi | pytest(マーカー `sudachi`) | 品詞の値、入力の上限(49,149バイト) | SudachiPyを上げるときに必ず通す |
| スナップショット | pytest(マーカー `snapshot`) | 本物の辞書で `data/standard-texts/` の3本を両モードで変換 | 差分が出たらレビューで判断 |
| E2E | Playwright | 機能設計書「E2Eテスト」のシナリオすべて(PC幅のChromium・WebKit、スマートフォン幅360px) | すべてのシナリオが通る |
| 性能 | pytest(マーカー `performance`)、Playwright | 50,000文字でサーバー処理1秒以内(CIでは2秒を超えたら失敗)。画面まで含めて10,000文字2秒・50,000文字5秒、スマートフォン相当で10,000文字4秒 | architecture.mdの目標 |

**カバレッジ**:
- 対象はプルリクエストのCIで動くテスト(`snapshot`・`performance` を除く)
- Python: 全体80%以上(`--cov-fail-under=80`)。加えて `s7/services/` と `s7builder/` はそれぞれ90%以上を、`coverage report --include='src/s7/services/*' --fail-under=90` のように別に確かめる(`scripts/check.sh` と `ci.yml` で実行)
- 画面: `@vitest/coverage-v8` の `thresholds` で80%以上

### pytestの設定

`server/pyproject.toml` に次を書く。

```toml
[tool.pytest.ini_options]
addopts = ["--import-mode=importlib", "--strict-markers", "-m", "not snapshot and not performance"]
pythonpath = ["tests"]
markers = [
  "sudachi: 本物のSudachiを使う(SudachiDict-coreがあれば動く)",
  "snapshot: 本物の変換用辞書が必要",
  "performance: 本物の変換用辞書が必要。時間を測る",
]
```

- 何も付けずに `pytest` を実行すると、本物の変換用辞書が要らないテストだけが動く。`-m "snapshot or performance"` を付けると、`addopts` の `-m` より後に書いたほうが使われ、辞書が要るテストだけが動く
- `tests/` 以下に `__init__.py` を置かない。テスト用の部品は `pythonpath` を使って `from fixtures.fake_tokenizer import FakeTokenizer` のように取り込む
- 本物の変換用辞書が要るテストは、辞書のファイルが無ければ失敗させる(気付かずに飛ばさないため)

### テストの書き方

**Python**: 関数名は `test_[対象]_[条件]_[期待結果]`。Given-When-Thenをコメントで区切る。

```python
def test_shift_single_sibling_climbs_to_parent(small_repo: DictionaryRepository) -> None:
    """兄弟が自分だけの概念は、上位語の兄弟グループでN個先に進む。"""
    # Given: 兄弟がいない概念を1つだけ持つ見出し語「三毛猫」(テスト用辞書)
    shifter = ConceptShifter(small_repo, SenseSelector(small_repo))
    lemma = small_repo.find_lemma("三毛猫")
    assert lemma is not None

    # When
    result = shifter.shift(lemma.id, n=1)

    # Then: 1段上がってから置き換わる(状態 climbed の判定は TransformService のテストで見る)
    assert result.shift is not None
    assert [step.to.id for step in result.shift.climbs] == ["90000002-n"]
```

- 照合規則のように入力と期待値の組が多いものは `pytest.mark.parametrize` で表にする。照合規則は、機能設計書「比較の例」の表の**すべての行**をそのまま並べる(下は書き方の例)

```python
@pytest.mark.parametrize(("smaller", "larger"), [
    ("はは", "ばば"),   # 清音 < 濁音
    ("ばば", "ぱぱ"),   # 濁音 < 半濁音
    ("しよう", "しょう"),  # 直音 < 小書き文字
    ("ああ", "あー"),   # 母音 < 長音
    ("あ", "ああ"),     # 短い方が先
    ("んん", "んー"),   # 母音の無い長音は末尾扱い
])
def test_sort_key_orders_by_collation_rule(smaller: str, larger: str) -> None:
    assert compute_sort_key(smaller) < compute_sort_key(larger)
```

- 形式名詞の一覧は、`formal_nouns.py` と、写しである機能設計書・用語集の一覧が一致することをテストで確かめる(`tests/unit/s7/services/test_formal_nouns.py`。ドキュメントの該当箇所を読んで比べる)

**TypeScript**: `describe` に対象、`it` に日本語で「条件 → 期待結果」を書く。

```typescript
describe('countChars', () => {
  it('絵文字を1文字として数える', () => {
    expect(countChars('猫🐈')).toBe(2);
  });
});
```

### テスト用の辞書とモック

- ユニット・統合テストは、本物の日本語WordNetではなく `tests/fixtures/wnjpn_sample.sql` から作る小さな辞書を使う(数十語。テストで使う語は架空の概念IDでよい)。`conftest.py` がセッションごとに1回ビルドし、`small_repo` として渡す
- 小さな辞書のビルドでは、読みの決定に `FakeTokenizer`(見出し語と読みの対応表を持つ)を使う。本物のSudachiの読みに左右されず、期待値を固定できるため
- Sudachiに依存しないテストは `FakeTokenizer` を使う。Sudachiの品詞の扱いと入力の上限を確かめるテストだけ本物を使い、マーカー `sudachi` を付ける
- サービスのテストでは、リポジトリをモックにせず小さな辞書を使う(モックの戻り値の作り込みより、本物の索引のほうが誤りを見つけやすいため)
- 画面のテストでは `ApiClient` をモックにする。`fetch` を直接モックにするのは `ApiClient` 自体のテストだけ

### スナップショットの更新

- 期待値は `server/tests/snapshot/expected/[テキスト名].[mode].json`
- 更新は `uv run --directory server pytest -m snapshot --update-snapshots` で行う(`--update-snapshots` は `conftest.py` で定義する)。更新したら差分を読み、意図した変化かをプルリクエストに書く

## 変換用辞書を変えるときの手順

次のどれかを変えると変換結果が変わる。`dict/[内容]` ブランチで、下の手順で行う。

- 照合規則(`gojuon_collation.py`)、形式名詞の除外リスト(`formal_nouns.py`)、置換先から除外する語のリスト(`data/excluded-lemmas.txt`)
- 元データ(日本語WordNet)、SudachiPy・SudachiDict-coreのバージョン
- 辞書ビルダーの処理(`s7builder/`)のうち、出力が変わるもの

**手順**:

1. `dict/[内容]` ブランチを作る
2. 変更を入れ、`s7builder/version.py` の `DICTIONARY_VERSION` を上げる。形式は `YYYY.MM.patch`。同じ月の中ではpatchを1つ上げ、月が変わったら新しい月の `0` にする(例: `2026.10.1` の次が11月なら `2026.11.0`)
3. 変えたものに応じて、付随するファイルを直す

   | 変えたもの | 付随して直すもの |
   |------------|------------------|
   | 日本語WordNet | `data/wnjpn.db.sha256`、`licenses/wordnet-ja.txt`(ライセンス文が変わった場合) |
   | SudachiPy・SudachiDict-core | `server/uv.lock`、`licenses/sudachi*.txt`、`licenses/generated/`(`scripts/generate-licenses.sh`)。`sudachi` マーカーのテストを通す |
   | 形式名詞の除外リスト | 写しである `docs/functional-design.md` と `docs/glossary.md` の一覧 |

4. `scripts/build-dictionary.sh` で辞書を作り直し、`data/reports/build-report.json` と `data/reports/quality-report.json` を更新する
5. スナップショットを更新し(「スナップショットの更新」)、差分が意図どおりかを確かめる
6. 置換率を基準値と比べる。`quality-report.json` の6つの値(標準の文章3本 × 2モード)それぞれを、`quality-baseline.json` の同じ値と比べ、**どれか1つでも5ポイント以上下がっていたら**プルリクエストに理由を書く(PRDの「辞書の品質の基準」)
   - 比べる相手は直前の版ではなく基準値。少しずつの低下が積み重なっても気付けるようにするため
   - 基準値を変えてよいのは、標準の文章を差し替えたときと、低下を受け入れるとプルリクエストで決めたときだけ。どちらもプルリクエストに理由を書く
7. `data/dictionary-history.md` に、新しいバージョンの見出しと変わった内容を書く。書式は `## [バージョン]([日付])` の見出しと `- ` の箇条書きだけ(`docs/repository-structure.md`「data/」。画面がこの書式だけを読むため)
8. プルリクエストの「変換結果への影響」に差分の要約を書く

**標準の文章(`data/standard-texts/`)を差し替える場合**: 辞書のバージョンは上げない。スナップショット、`quality-report.json`、`quality-baseline.json` をまとめて取り直し、出典をファイルの先頭に書く。

## 依存関係の更新

- Dependabotで週1回、プルリクエストを作る。対象は `uv`(`server/`)、`npm`(`web/`)、`docker`、`github-actions`。同じ対象の更新は `groups` で1つのプルリクエストにまとめ、実行時の依存関係と開発用の依存関係でグループを分ける
- React・Vite・FastAPI・Pydanticなどのメジャーバージョンの更新はグループから外し、1つずつ判断する
- SudachiPy、SudachiDict-coreはDependabotの対象から外し(`ignore`)、上の「変換用辞書を変えるときの手順」で更新する。セキュリティの警告が出たら、2週間以内に取り込むかを判断する
- コンテナのベースイメージはタグとダイジェストで固定し、Dependabotの更新で上げる

**脆弱性の検査**:

| 対象 | コマンド | 失敗させる条件 |
|------|----------|----------------|
| Python(実行時の依存関係) | `uv export --no-dev --format requirements-txt \| pip-audit -r -` | 既知の脆弱性が1つでもある(`pip-audit` は深刻度で絞れないため) |
| 画面(画面に含まれる依存関係) | `npm audit --omit=dev --audit-level=high` | 深刻度が高(high)以上 |

- 修正版がまだ無い脆弱性は、影響を調べたうえで、`--ignore-vuln [ID]`(pip-audit)などで一時的に外してよい。外すときは `ci.yml` に理由と見直す日(30日以内)をコメントで書く

**ライセンス**: 依存関係を追加するときは、ライセンスが次の許可リストにあることを確かめ、プルリクエストに書く。

| 扱い | ライセンス |
|------|------------|
| 使ってよい | MIT、BSD-2-Clause、BSD-3-Clause、Apache-2.0、ISC、0BSD、PSF-2.0、Python-2.0、CC0-1.0、Unlicense |
| 改変しない場合だけ使ってよい | MPL-2.0 |
| 使わない | GPL、LGPL、AGPL、SSPL、ライセンスの書かれていないもの |
| それ以外 | プルリクエストで相談して決め、この表に足す |

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | 入れ方 |
|--------|-----------|--------|
| Python | 3.13 | Dev Container(`.devcontainer/devcontainer.json` の features) |
| uv | 最新 | 同上 |
| Node.js | 24 LTS | 同上 |
| Playwrightのブラウザ | `web/package-lock.json` のPlaywrightに合わせる | 下の手順2(`npm run e2e:install`) |
| Docker | - | ホスト側。コンテナのビルドを手元で確かめる場合だけ |

Dockerに割り当てるメモリは4GB以上にする(辞書のビルドで使う)。

**Dev Containerの設定に足すもの**(実装の初回の作業。今の `devcontainer.json` はPython・uv・Node.jsだけを入れている):
- `postCreateCommand`: 下の手順2を自動で実行する
- `forwardPorts`: `8000`(API)、`5173`(画面)
- VS Codeの拡張機能: Ruff、ESLint、Prettier、Playwright、ShellCheck
- `hostRequirements.memory`: `4gb`(足りなければ警告を出す)
- ShellCheckのインストール
- あわせて、`docs/repository-structure.md`「除外設定」の `.gitignore` の追加分を入れる(入れる前に依存関係を入れると、`.venv/` や `node_modules/` がコミットの対象に見えるため)

### セットアップ手順

```bash
# 1. Dev Containerでリポジトリを開く

# 2. 依存関係を入れる(CIでは uv sync --locked と npm ci を使う)
uv sync --directory server
npm ci --prefix web
npm run e2e:install --prefix web

# 3. 日本語WordNetを取得し、変換用辞書を作る(初回のみ。数分かかる)
scripts/fetch-wordnet.sh
scripts/build-dictionary.sh

# 4. 開発サーバーを起動する(API: http://localhost:8000、画面: http://localhost:5173)
scripts/dev.sh
```

- 環境変数は不要(既定値で動く)。変える場合は `.env.example` を `.env` にコピーして編集する。`scripts/dev.sh` は、`.env` があればサーバーに渡す(`uv run --env-file`)。サーバー自身は `.env` を読まず、環境変数だけを読む
- 辞書のビルドを省いてテストだけ動かす場合、手順3は不要(テストは小さな辞書を自動で作る)

### よく使うコマンド

| 目的 | コマンド |
|------|---------|
| すべての確認 | `scripts/check.sh` |
| Pythonのテスト(本物の辞書が不要なもの) | `uv run --directory server pytest` |
| 一部のテストだけ | `uv run --directory server pytest tests/unit/s7/services -k concept`(パスは `server/` から書く) |
| 本物の辞書が必要なテストだけ | `uv run --directory server pytest -m "snapshot or performance"` |
| 画面のテスト | `npm test --prefix web` |
| E2Eテスト | `npm run e2e --prefix web` |
| APIの型を作り直す | `scripts/generate-api-types.sh` |
| ライセンス一覧を作り直す | `scripts/generate-licenses.sh` |
| 報告がコミット済みのものと一致するか確かめる | `scripts/check-reports.sh` |
| コンテナを手元でビルド | `docker build -t s7-maker .`(ホスト側で実行する。Dev Containerの中にはDockerが無い) |

- Pythonのツールは `uv run --directory server` で実行する(作業ディレクトリが `server/` になり、`server/pyproject.toml` の設定が読まれる。`--project` は作業ディレクトリを変えないため使わない)
- `--directory server` の中では、パスの基準が `server/` になる。テストのパスは `tests/...` と書き、`data/` などリポジトリ直下のファイルは `../data/...` か絶対パスで渡す
