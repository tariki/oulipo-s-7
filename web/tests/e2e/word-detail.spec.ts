import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

const TEXT = '吾輩は猫である。名前はまだ無い。';

test('語を選ぶと置換経路が出て、置き換えない指定はルールや N を変えても保たれる', async ({
  page,
}) => {
  const api = await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();

  await page.getByRole('button', { name: '獅子、元の語は猫' }).click();
  const detail = page.getByRole('region', { name: '選んだ語: 猫 → 獅子' });
  await expect(detail).toBeVisible();
  await expect(detail.getByRole('listitem')).toHaveText([
    '猫(元の語)',
    '猫科',
    '猫背',
    '獅子(変換後の語)',
  ]);

  await detail.getByRole('button', { name: 'この語は置き換えない' }).click();
  await expect(page.getByRole('button', { name: '猫、置き換えない指定' })).toBeVisible();
  expect(api.transformRequests.at(-1)).toEqual({
    text: TEXT,
    mode: 'gojuon',
    n: 7,
    exclusions: [0],
  });

  // ルールと N を変えて変換し直しても、指定は保たれる
  await page.getByRole('radio', { name: '概念版' }).check();
  await page.getByLabel('N').fill('3');
  await page.getByRole('button', { name: '変換する' }).click();
  await expect.poll(() => api.transformRequests.length).toBe(3);
  expect(api.transformRequests.at(-1)).toEqual({
    text: TEXT,
    mode: 'concept',
    n: 3,
    exclusions: [0],
  });
  await expect(page.getByRole('button', { name: '猫、置き換えない指定' })).toBeVisible();
});

test('概念版で語義を選び直すと、その語だけが置き換え直される', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('radio', { name: '概念版' }).check();
  await page.getByRole('button', { name: '変換する' }).click();

  await page.getByRole('button', { name: '虎、元の語は猫、上の階層から置き換え' }).click();
  const detail = page.getByRole('region', { name: '選んだ語: 猫 → 虎' });
  await expect(detail.getByText('兄弟の概念が無いため、階層を上がりました。')).toBeVisible();
  await expect(detail.getByRole('radio', { name: '猫・ネコ ネコ科の動物' })).toBeChecked();

  await detail.getByRole('radio', { name: '猫 三味線のこと' }).check();
  await expect(page.getByRole('radio', { name: '猫 三味線のこと' })).toBeChecked();

  await expect(page.getByRole('button', { name: '三味線、元の語は猫' })).toBeVisible();
  await expect(page.getByRole('button', { name: '名称、元の語は名前' })).toBeVisible();
  expect(api.transformRequests.at(-1)).toEqual({
    text: TEXT,
    mode: 'concept',
    n: 7,
    senseOverrides: { '0': '10000001-n' },
  });
});

test('キーボードだけで、語を選び、面で操作し、Esc で語に戻れる', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await page.getByLabel('文章').fill(TEXT);
  await page.getByRole('button', { name: '変換する' }).click();
  const token = page.getByRole('button', { name: '獅子、元の語は猫' });
  await token.focus();

  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: '選んだ語: 猫 → 獅子' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: '閉じる' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'この語は置き換えない' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: '猫、置き換えない指定' })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page.getByRole('region', { name: /選んだ語/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '猫、置き換えない指定' })).toBeFocused();
});
