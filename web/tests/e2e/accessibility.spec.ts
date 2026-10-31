import { AxeBuilder } from '@axe-core/playwright';
import { type Page, expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

async function expectNoViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

test('入力待ち', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await expect(page.getByRole('button', { name: '変換する' })).toBeVisible();

  await expectNoViolations(page);
});

test('結果表示', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill('吾輩は猫である。名前はまだ無い。');
  await page.getByRole('button', { name: '変換する' }).click();
  await expect(page.getByRole('button', { name: '獅子、元の語は猫' })).toBeVisible();

  await expectNoViolations(page);
});

test('エラー', async ({ page }) => {
  await mockApi(page, { transformStatus: 500 });
  await page.goto('/');
  await page.getByLabel('文章').fill('猫');
  await page.getByRole('button', { name: '変換する' }).click();
  await expect(page.getByRole('alert')).toBeVisible();

  await expectNoViolations(page);
});

test('このアプリについて', async ({ page }) => {
  await mockApi(page);
  await page.goto('/about');
  await expect(page.getByRole('heading', { level: 1, name: 'このアプリについて' })).toBeVisible();

  await expectNoViolations(page);
});
