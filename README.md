# S+7メーカー

文章中の名詞を、辞書でN個先の語に置き換えるWebアプリです。OuLiPo(潜在文学工房)の「S+7」という言葉遊びを、日本語の文章で試せます。

- **五十音順S+N**: 名詞を、五十音順に並べた辞書でN個先の語に置き換えます
- **概念版S+N**: 日本語WordNetの概念の階層を使い、同じ上位概念を持つ兄弟の概念のうちN個先の語に置き換えます

> 開発中です。いまは土台(開発環境、ツールの設定、CI)だけがあります。

## ドキュメント

| ドキュメント | 内容 |
|--------------|------|
| [プロダクト要求定義書](docs/product-requirements.md) | 何を作るか、なぜ作るか |
| [機能設計書](docs/functional-design.md) | 機能、アルゴリズム、API、画面 |
| [技術仕様書](docs/architecture.md) | 技術スタック、構成、性能、セキュリティ |
| [リポジトリ構造定義書](docs/repository-structure.md) | ディレクトリとファイルの置き場所、依存の向き |
| [開発ガイドライン](docs/development-guidelines.md) | コーディング規約、Git運用、テスト、手元の確認とCI |
| [用語集](docs/glossary.md) | このプロジェクトの用語 |

## セットアップ

Dev Containerで開くと、依存関係の導入まで自動で行います(`.devcontainer/post-create.sh`)。手順の詳細は[開発ガイドライン「開発環境セットアップ」](docs/development-guidelines.md#開発環境セットアップ)を見てください。

```bash
# 依存関係を入れる(Dev Containerでは自動)
uv sync --directory server
npm ci --prefix web

# 開発サーバーを起動する(API: http://localhost:8000、画面: http://localhost:5173)
scripts/dev.sh

# プルリクエストを出す前の確認(リント、型チェック、テスト、ビルド)
scripts/check.sh
```

環境変数は不要です(既定値で動きます)。変える場合は `.env.example` を `.env` にコピーして編集してください。

## ライセンスとクレジット

辞書データとライブラリのライセンス表示は、変換用辞書と画面を作る作業で `licenses/` と「このアプリについて」の画面に加えます(日本語WordNet、SudachiPy、SudachiDict)。
