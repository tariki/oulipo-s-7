"""変換用辞書のエンティティ。

機能設計書「変換用辞書のエンティティ」の実装。辞書ビルダーが作り、サーバーが読み込む。
"""

from dataclasses import dataclass
from typing import Literal

ParentRelation = Literal["hypernym", "instance_hypernym"]


@dataclass(frozen=True, slots=True)
class Lemma:
    """見出し語。同じ表記の語は、語義が複数あっても1つにまとめる。

    Attributes:
        id: 見出し語の番号(0始まり)。読みのある語の五十音順、続けて読みの無い語の表記順。
        surface: 表記。日本語WordNetの見出し語そのまま。
        reading: 読み(ひらがな)。決まらない場合はNone。
        sort_key: 並び替え用のキー。読みが無ければNone。
    """

    id: int
    surface: str
    reading: str | None
    sort_key: str | None


@dataclass(frozen=True, slots=True)
class Synset:
    """名詞の概念。

    Attributes:
        id: 日本語WordNetの概念ID(例: "02084071-n")。
        parent_id: 選ばれた上位語の概念ID。最上位ならNone。
        parent_relation: parent_id を選んだ関係。parent_id がNoneならNone。
        sibling_group_id: 所属する兄弟グループ。
        sibling_index: 兄弟グループ内での位置(0始まり)。
        representative_lemma_id: 代表語(この概念の見出し語のうち Lemma.id が最小のもの)。
        definition_ja: 日本語の定義文。
        definition_en: 英語の定義文。
    """

    id: str
    parent_id: str | None
    parent_relation: ParentRelation | None
    sibling_group_id: int | None
    sibling_index: int | None
    representative_lemma_id: int | None
    definition_ja: str | None
    definition_en: str | None


@dataclass(frozen=True, slots=True)
class SiblingGroup:
    """同じ上位語を持ち、代表語を持つ概念の並び。

    Attributes:
        id: 兄弟グループの番号。
        parent_id: 共通の上位語の概念ID。
        member_ids: 兄弟概念の概念ID。代表語の Lemma.id → 概念ID の順。
    """

    id: int
    parent_id: str
    member_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Sense:
    """見出し語の語義(見出し語と概念の組)。

    Attributes:
        lemma_id: 見出し語の番号。
        synset_id: 概念ID。
        score: 語義の選択に使う頻度スコア(英語の語義頻度の合計)。
        rank: 同じ見出し語の語義の中での順位(0が既定で選ばれる語義)。
    """

    lemma_id: int
    synset_id: str
    score: int
    rank: int


@dataclass(frozen=True, slots=True)
class DictionaryMeta:
    """変換用辞書のメタ情報。

    Attributes:
        dictionary_version: 変換用辞書のバージョン(例: "2026.10.0")。
        wordnet_version: 元データのバージョン("wnjpn-1.1")。
        sudachidict_version: 読みの決定に使ったSudachiDict(例: "core-20261015")。
        built_at: 辞書のバージョンを決めた日(ISO 8601)。ビルドの決定性のため実行時刻は使わない。
        lemma_count: 見出し語の数(読みの無い語を含む)。
        gojuon_lemma_count: 五十音順リストの語数(読みのある見出し語の数)。
        synset_count: 概念の数。
    """

    dictionary_version: str
    wordnet_version: str
    sudachidict_version: str
    built_at: str
    lemma_count: int
    gojuon_lemma_count: int
    synset_count: int
