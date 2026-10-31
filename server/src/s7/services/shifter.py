"""五十音順S+Nと概念版S+Nで共有する、N個先の計算(機能設計書「N個先の計算」)。

2つの Shifter は引数が違う(語義の上書きの有無)ため、共通のインターフェースは作らず、
計算だけを共有する。
"""


def shift_index(index: int, n: int, size: int) -> tuple[int, bool]:
    """リスト上の位置 index から n 個先の位置と、末尾を超えて先頭に戻ったかを返す。

    Args:
        index: 元の位置(0始まり)。
        n: いくつ先に進むか(1以上)。
        size: リストの大きさ(1以上)。

    Returns:
        (n 個先の位置, 末尾を超えて先頭に戻ったか)。
    """
    return (index + n) % size, index + n >= size
