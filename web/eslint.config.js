// @ts-check
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import prettier from 'eslint-config-prettier';
import { createTypeScriptImportResolver } from 'eslint-import-resolver-typescript';
import { importX } from 'eslint-plugin-import-x';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import { configs as tsConfigs } from 'typescript-eslint';

// --- 依存の向き(docs/repository-structure.md「画面の依存」) ---

const DIRECTORIES = [
  'pages',
  'hooks',
  'components',
  'api',
  'segments',
  'text',
  'about',
  'analytics',
];

/**
 * ディレクトリごとに、取り込んでよい先を決める。
 * apiTypes は api/types.ts だけを取り込めることを表す。'type' なら型の取り込みに限る。
 * @type {Record<string, { allow: string[]; apiTypes: 'any' | 'type' | 'none' }>}
 */
const DEPENDENCY_RULES = {
  pages: {
    allow: ['pages', 'hooks', 'components', 'analytics', 'about', 'segments', 'text'],
    apiTypes: 'any',
  },
  hooks: { allow: ['hooks', 'api', 'analytics', 'segments', 'text'], apiTypes: 'any' },
  components: { allow: ['components', 'segments', 'text'], apiTypes: 'type' },
  analytics: { allow: ['analytics', 'api'], apiTypes: 'any' },
  about: { allow: ['about'], apiTypes: 'type' },
  segments: { allow: ['segments'], apiTypes: 'type' },
  text: { allow: ['text'], apiTypes: 'type' },
  api: { allow: ['api'], apiTypes: 'any' },
};

/** @param {string} directory */
function dependencyRuleFor(directory) {
  const { allow, apiTypes } = DEPENDENCY_RULES[directory] ?? { allow: [], apiTypes: 'none' };
  const forbidden = DIRECTORIES.filter((d) => !allow.includes(d) && d !== 'api');
  /** @type {Array<{ group: string[]; message: string; allowTypeImports?: boolean }>} */
  const patterns = forbidden.map((d) => ({
    group: [`**/${d}`, `**/${d}/**`],
    message: `${directory}/ から ${d}/ には依存できません(docs/repository-structure.md「画面の依存」)`,
  }));
  if (!allow.includes('api')) {
    // api/ のうち types.ts 以外は使えない
    patterns.push({
      group: ['**/api/**', '!**/api/types', '!**/api/types.ts'],
      message: `${directory}/ からは api/types.ts だけを取り込めます`,
    });
    if (apiTypes === 'type') {
      patterns.push({
        group: ['**/api/types', '**/api/types.ts'],
        allowTypeImports: true,
        message: `${directory}/ からは api/types.ts の型だけを取り込めます(import type を使う)`,
      });
    }
  }
  // 自動生成の型は api/types.ts からだけ参照する
  patterns.push({
    group: ['**/api/generated/**', '**/api/generated'],
    message: 'api/generated/ は api/types.ts からだけ取り込めます',
  });
  return {
    files: [`src/${directory}/**/*.{ts,tsx}`],
    ignores: directory === 'api' ? ['src/api/types.ts'] : [],
    rules: { 'no-restricted-imports': ['error', { patterns }] },
  };
}

export default defineConfig(
  {
    ignores: [
      'dist/',
      'coverage/',
      'node_modules/',
      'src/api/generated/',
      'playwright-report/',
      'test-results/',
    ],
  },
  js.configs.recommended,
  tsConfigs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    ...react.configs.flat.recommended,
    languageOptions: {
      ...react.configs.flat.recommended.languageOptions,
      globals: globals.browser,
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...react.configs.flat['jsx-runtime'].rules,
      'react/no-danger': 'error',
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    ...reactHooks.configs.flat['recommended-latest'],
  },
  {
    files: ['**/*.{ts,tsx}'],
    ...jsxA11y.flatConfigs.recommended,
  },
  importX.flatConfigs.recommended,
  importX.flatConfigs.typescript,
  {
    settings: {
      'import-x/resolver-next': [createTypeScriptImportResolver()],
    },
    rules: {
      'import-x/no-cycle': 'error',
      'no-console': 'error',
    },
  },
  // 同じルールを複数の設定で書くと後のものが前を上書きするため、no-restricted-imports は
  // ディレクトリごとに1つの設定にまとめる。pages/ への依存の禁止もここに含まれる
  // (pages/ を許すのは pages/ 自身だけ。src/ 直下の App.tsx・main.tsx は対象外)
  ...DIRECTORIES.map(dependencyRuleFor),
  {
    files: ['**/*.js'],
    ...tsConfigs.disableTypeChecked,
    languageOptions: {
      ...tsConfigs.disableTypeChecked.languageOptions,
      globals: globals.node,
    },
  },
  prettier,
);
