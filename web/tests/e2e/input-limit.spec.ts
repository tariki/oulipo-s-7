import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

test('50,000文字を超えると変換ボタンを押せない', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  const button = page.getByRole('button', { name: '変換する' });

  await page.getByLabel('文章').fill('あ'.repeat(50_000));
  await expect(button).toBeEnabled();
  await expect(page.getByText('50,000 / 50,000')).toBeVisible();

  await page.getByLabel('文章').fill('あ'.repeat(50_001));
  await expect(button).toBeDisabled();
  await expect(page.getByText(/50,000文字以内で入力してください/)).toBeVisible();
});

test('絵文字は1文字として数える', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  await page.getByLabel('文章').fill('猫🐈');

  await expect(page.getByText('2 / 50,000')).toBeVisible();
});
