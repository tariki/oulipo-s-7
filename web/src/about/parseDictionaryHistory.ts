/** 辞書バージョンの更新履歴の1件。 */
export interface DictionaryRelease {
  version: string;
  date: string;
  changes: string[];
}

/** 見出しの書式: `## 2026.10.0(2026-10-31)`(括弧は全角・半角のどちらでもよい)。 */
const HEADING = /^## (\S+?)[(（](\d{4}-\d{2}-\d{2})[)）]\s*$/;
const ITEM = /^- (.+)$/;

/**
 * data/dictionary-history.md を読む。決まった書式(見出しと箇条書き)だけを読み、ほかの行は無視する
 * (Markdownの描画ライブラリや dangerouslySetInnerHTML を使わずにReactで描くため)。
 */
export function parseDictionaryHistory(text: string): DictionaryRelease[] {
  const releases: DictionaryRelease[] = [];
  for (const line of text.split(/\r?\n/)) {
    const heading = HEADING.exec(line);
    if (heading?.[1] !== undefined && heading[2] !== undefined) {
      releases.push({ version: heading[1], date: heading[2], changes: [] });
      continue;
    }
    const item = ITEM.exec(line);
    const current = releases.at(-1);
    if (item?.[1] !== undefined && current !== undefined) {
      current.changes.push(item[1]);
    }
  }
  return releases;
}
