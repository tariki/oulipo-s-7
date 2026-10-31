import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

const TEXT = '吾輩は猫である。名前はまだ無い。';

test('文章を変換し、語の説明を見て、結果をコピーできる', async ({ page, context, browserName }) => {
  const api = await mockApi(page);
  if (browserName === 'chromium') {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  }
  await page.goto('/');

  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();

  // 置き換えた語のハイライトと、元の語の説明
  const token = page.getByRole('button', { name: '獅子、元の語は猫' });
  await expect(token).toBeVisible();
  await token.click();
  await expect(page.getByRole('note').filter({ hasText: '元の語: 猫' })).toBeVisible();

  // コピー
  await page.getByRole('button', { name: 'コピー' }).click();
  await expect(page.getByText('コピーしました')).toBeVisible();
  if (browserName === 'chromium') {
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
      '吾輩は獅子である。名字はまだ無い。',
    );
  }
  await expect
    .poll(() => api.events.map((e) => e.event))
    .toEqual(['page_view', 'transform', 'copy']);
  // 解析のイベントに本文や語を入れない
  expect(JSON.stringify(api.events)).not.toContain('猫');
});

test('概念版に切り替えて変換し直しても、入力が残る', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();
  await expect(page.getByRole('button', { name: '獅子、元の語は猫' })).toBeVisible();

  await page.getByRole('radio', { name: '概念版' }).check();
  await page.getByLabel('N').fill('3');
  await page.getByRole('button', { name: '変換する' }).click();

  await expect(
    page.getByRole('button', { name: '虎、元の語は猫、上の階層から置き換え' }),
  ).toBeVisible();
  await expect(page.getByLabel('文章')).toHaveValue(TEXT);
  expect(api.transformRequests.at(-1)).toEqual({ text: TEXT, mode: 'concept', n: 3 });
});

test('スマートフォン幅では、変換後の文章を原文より先に表示する', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-360', 'スマートフォン幅だけ');
  await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();

  const replaced = await page.getByRole('heading', { name: '変換後' }).boundingBox();
  const original = await page.getByRole('heading', { name: '原文' }).boundingBox();
  expect(replaced?.y).toBeLessThan(original?.y ?? 0);
  // 横にはみ出さない
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(360);
});

test('スマートフォン幅では、このアプリについても横にはみ出さない', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-360', 'スマートフォン幅だけ');
  await mockApi(page);
  await page.goto('/about');
  await expect(page.getByRole('heading', { level: 1, name: 'このアプリについて' })).toBeVisible();

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(360);
});

test('失敗しても入力は残り、エラーを表示する', async ({ page }) => {
  await mockApi(page, { transformStatus: 500 });
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();

  await expect(page.getByRole('alert')).toContainText('変換に失敗しました');
  await expect(page.getByLabel('文章')).toHaveValue(TEXT);
});
