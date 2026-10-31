import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

test('準備中に押した変換は、準備ができ次第自動で実行する', async ({ page }) => {
  const api = await mockApi(page, { metaStatuses: [503, 503, 503] });
  await page.goto('/');

  await expect(page.getByRole('main').getByText(/準備中です/)).toBeVisible();
  await page.getByLabel('文章').fill('吾輩は猫である。');
  await page.getByRole('button', { name: '変換する' }).click();
  await expect(page.getByRole('button', { name: '準備ができ次第変換します' })).toBeVisible();

  // 準備ができたら自動で変換する
  await expect(page.getByRole('button', { name: '獅子、元の語は猫' })).toBeVisible({
    timeout: 10_000,
  });
  expect(api.transformRequests).toHaveLength(1);
  await expect(page.getByRole('main').getByText(/準備中です/)).toBeHidden();
});

test('待っている間に文章を変えたら、保持した変換を捨てる', async ({ page }) => {
  const api = await mockApi(page, { metaStatuses: [503, 503] });
  await page.goto('/');
  await page.getByLabel('文章').fill('吾輩は猫である。');
  await page.getByRole('button', { name: '変換する' }).click();
  await expect(page.getByRole('button', { name: '準備ができ次第変換します' })).toBeVisible();

  await page.getByLabel('文章').fill('吾輩は犬である。');

  await expect(page.getByRole('button', { name: '変換する' })).toBeVisible();
  await expect(page.getByRole('main').getByText(/準備中です/)).toBeHidden({ timeout: 10_000 });
  expect(api.transformRequests).toHaveLength(0);
});
