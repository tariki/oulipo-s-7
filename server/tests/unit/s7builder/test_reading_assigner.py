import pytest
from fixtures.fake_tokenizer import FakeTokenizer

from s7.domain.text import Morpheme, SplitMode
from s7builder.reading_assigner import Reading, ReadingAssigner


@pytest.fixture
def assigner() -> ReadingAssigner:
    return ReadingAssigner(
        FakeTokenizer(
            {
                "図書館": "トショカン",
                "猫": "ネコ",
                "東京湾": ["トウキョウ", "ワン"],  # モードCでも2形態素になる語
                "ＤＮＡ": "ディーエヌエー",
                "B-52": "b-ゴニ",  # かな以外が混ざる読み
                "猫・犬": "ネコ・イヌ",
                "記号": "",  # 空になる読み
            }
        )
    )


@pytest.mark.parametrize(
    ("surface", "reading"),
    [
        ("ねこ", "ねこ"),  # ひらがな
        ("アイサ", "あいさ"),  # カタカナ(Sudachiでは未知語でも、かなだけの表記で決まる)
        ("ル・コルビュジエ", "るこるびゅじえ"),  # 中黒を除く
        ("ローマ", "ろーま"),  # 長音はそのまま
        ("ヴァイオリン", "ゔぁいおりん"),  # ヴ → ゔ
        ("ヵ", "ゕ"),  # ヵ → ゕ
        ("ヶ", "ゖ"),
        ("ー", "ー"),  # 長音だけでも読みにする
    ],
)
def test_assign_kana_only_surface(assigner: ReadingAssigner, surface: str, reading: str) -> None:
    assert assigner.assign(surface) == Reading(reading, "kana")


def test_assign_kana_only_with_char_not_in_hiragana_returns_none(
    assigner: ReadingAssigner,
) -> None:
    """ヷ はひらがなに無いため、かなだけの表記でも読みは決まらない。"""
    assert assigner.assign("ヷ") is None


def test_assign_only_middle_dots_returns_none(assigner: ReadingAssigner) -> None:
    """中黒を除くと空になる表記は読みが決まらない(手順4)。"""
    assert assigner.assign("・・") is None


@pytest.mark.parametrize(
    ("surface", "reading"),
    [
        ("図書館", "としょかん"),
        ("東京湾", "とうきょうわん"),  # 形態素の読みをつなげる
        ("ＤＮＡ", "でぃーえぬえー"),
        ("猫・犬", "ねこいぬ"),  # 読みの中黒も除く
    ],
)
def test_assign_uses_sudachi_reading(assigner: ReadingAssigner, surface: str, reading: str) -> None:
    assert assigner.assign(surface) == Reading(reading, "sudachi")


def test_assign_oov_returns_none(assigner: ReadingAssigner) -> None:
    """形態素のうち1つでも未知語なら読みは決まらない。"""
    assert assigner.assign("未登録語") is None


def test_assign_reading_with_non_kana_returns_none(assigner: ReadingAssigner) -> None:
    """読みにかな以外が混ざれば読みは決まらない(手順3)。"""
    assert assigner.assign("B-52") is None


def test_assign_empty_reading_returns_none(assigner: ReadingAssigner) -> None:
    """Sudachiの読みが空なら読みは決まらない(手順4)。"""
    assert assigner.assign("記号") is None


def test_assign_symbol_with_placeholder_reading_returns_none() -> None:
    """Sudachiが記号・空白に付ける仮の読み「キゴウ」を、読みとして使わない。"""
    # Given: 「夫々」の「々」は補助記号で、読みが「キゴウ」になる
    symbol = Morpheme("々", "々", "キゴウ", ("補助記号", "一般", "*", "*", "*", "*"), is_oov=False)
    noun = Morpheme("夫", "夫", "オット", ("名詞", "普通名詞", "一般", "*", "*", "*"), is_oov=False)
    assigner = ReadingAssigner(_FixedTokenizer([noun, symbol]))

    # When / Then
    assert assigner.assign("夫々") is None


def test_assign_symbol_with_own_reading_is_kept() -> None:
    """記号でも、読みが付いていれば使う(例: 「＆」→「アンド」)。"""
    symbol = Morpheme("＆", "＆", "アンド", ("補助記号", "一般", "*", "*", "*", "*"), is_oov=False)
    assigner = ReadingAssigner(_FixedTokenizer([symbol]))

    assert assigner.assign("＆") == Reading("あんど", "sudachi")


class _FixedTokenizer:
    def __init__(self, morphemes: list[Morpheme]) -> None:
        self._morphemes = morphemes

    def tokenize(self, text: str, mode: SplitMode) -> list[Morpheme]:
        return self._morphemes
