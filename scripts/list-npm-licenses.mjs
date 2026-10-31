// 標準入力の `npm ls --parseable` の出力(パッケージのディレクトリの一覧)から、
// 名前・版・ライセンスと、ライセンスファイルの全文を出す。scripts/generate-licenses.sh から使う。
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.argv[2];
const directories = readFileSync(0, 'utf8').split('\n').filter(Boolean);
const lines = new Set();
const texts = new Map();
// 全文を載せるファイル(MIT・BSD などは著作権表示とライセンス文の再掲を求めるため)
const LICENSE_FILE = /^(licen[cs]e|copying|notice|authors)/i;
for (const directory of directories) {
  // 先頭の行は画面そのもの(web/)
  if (relative(root, directory) === '') {
    continue;
  }
  const pkg = JSON.parse(readFileSync(join(directory, 'package.json'), 'utf8'));
  const license = typeof pkg.license === 'string' ? pkg.license : 'UNKNOWN';
  const id = `${pkg.name} ${pkg.version}`;
  lines.add(`${id} ${license}`);
  for (const file of readdirSync(directory).sort()) {
    if (LICENSE_FILE.test(file)) {
      texts.set(`${id}: ${file}`, readFileSync(join(directory, file), 'utf8').trimEnd());
    }
  }
}
process.stdout.write('# 画面に含まれるnpmの依存関係(scripts/generate-licenses.sh で生成)\n');
process.stdout.write([...lines].sort().join('\n') + '\n');
for (const key of [...texts.keys()].sort()) {
  process.stdout.write(`\n===== ${key} =====\n\n${texts.get(key)}\n`);
}
