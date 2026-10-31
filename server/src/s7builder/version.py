"""変換用辞書のバージョン。

上げる条件と手順は docs/development-guidelines.md「変換用辞書を変えるときの手順」。
上げたら data/dictionary-history.md に同じバージョンと日付で追記する。
"""

from typing import Final

# YYYY.MM.patch
DICTIONARY_VERSION: Final = "2026.10.0"
# バージョンを決めた日(DictionaryMeta.built_at)。実行時刻を使うとビルドごとに結果が変わるため
DICTIONARY_DATE: Final = "2026-10-31"
WORDNET_VERSION: Final = "wnjpn-1.1"
