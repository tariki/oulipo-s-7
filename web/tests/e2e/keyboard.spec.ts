import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

test('キーボードだけで変換から語の選択まで操作できる', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  // 入力欄までTabで進んで入力する
  const textarea = page.getByLabel('文章');
  for (
    let i = 0;
    i < 10 && !(await textarea.evaluate((el) => el === document.activeElement));
    i += 1
  ) {
    await page.keyboard.press('Tab');
  }
  await expect(textarea).toBeFocused();
  await page.keyboard.type('吾輩は猫である。名前はまだ無い。');

  // 変換ボタンまでTabで進んで押す
  const button = page.getByRole('button', { name: '変換する' });
  for (
    let i = 0;
    i < 10 && !(await button.evaluate((el) => el === document.activeElement));
    i += 1
  ) {
    await page.keyboard.press('Tab');
  }
  await expect(button).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: '獅子、元の語は猫' })).toBeVisible();

  // ページの先頭のスキップリンクまで Shift+Tab で戻り、結果へ移る。Tabで最初の語、矢印キーで次の語へ
  const skipLink = page.getByRole('link', { name: '結果へ移動' });
  for (
    let i = 0;
    i < 15 && !(await skipLink.evaluate((el) => el === document.activeElement));
    i += 1
  ) {
    await page.keyboard.press('Shift+Tab');
  }
  await expect(skipLink).toBeFocused();
  await page.keyboard.press('Enter');
  // 結果の中は、見出しの横のコピー、変換後の最初の語の順
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'コピー' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: '獅子、元の語は猫' })).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('button', { name: '名字、元の語は名前' })).toBeFocused();
  // 語の説明はフォーカスでも出る
  await expect(page.getByRole('note').filter({ hasText: '元の語: 名前' })).toBeVisible();
});
