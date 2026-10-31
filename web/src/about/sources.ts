// 「このアプリについて」で表示するテキスト。web/ の外のファイルを ?raw で読み込む唯一の場所
// (vite.config.ts の server.fs.allow で ../licenses と ../data を許している)。
import dictionaryHistory from '../../../data/dictionary-history.md?raw';
import pythonLicenses from '../../../licenses/generated/python.txt?raw';
import webLicenses from '../../../licenses/generated/web.txt?raw';
import sudachiDictLicense from '../../../licenses/sudachidict-LICENSE.txt?raw';
import sudachiDictNotice from '../../../licenses/sudachidict-NOTICE.txt?raw';
import sudachiPyLicense from '../../../licenses/sudachipy-LICENSE.txt?raw';
import wordnetLicense from '../../../licenses/wordnet-ja.txt?raw';

export interface LicenseText {
  title: string;
  text: string;
}

/** 出典とライセンスの全文(表示する順)。 */
export const LICENSE_TEXTS: readonly LicenseText[] = [
  { title: '日本語WordNet 1.1', text: wordnetLicense },
  { title: 'SudachiDict(ライセンス)', text: sudachiDictLicense },
  { title: 'SudachiDict(NOTICE)', text: sudachiDictNotice },
  { title: 'SudachiPy', text: sudachiPyLicense },
  { title: 'サーバーの依存ライブラリ', text: pythonLicenses },
  { title: '画面の依存ライブラリ', text: webLicenses },
];

export const DICTIONARY_HISTORY: string = dictionaryHistory;
