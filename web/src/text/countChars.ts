/**
 * 文字数をUnicodeのコードポイント数で数える(Pythonの len() と一致する)。
 *
 * 画面で文字数を数える唯一の関数(開発ガイドライン「文字数はコードポイントで数える」)。
 * text.length はUTF-16の単位数で、絵文字を2文字と数えてサーバーとずれるため使わない。
 */
export function countChars(text: string): number {
  // 文字列のスプレッドはコードポイントごとに分ける。サーバーと数を合わせるため、
  // 書記素(絵文字の組み合わせなど)ではなくコードポイントで数えるのが意図どおり
  // eslint-disable-next-line @typescript-eslint/no-misused-spread
  return [...text].length;
}
