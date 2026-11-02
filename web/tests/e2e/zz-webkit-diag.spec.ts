// 一時的な調査用(WebKit で変換し直した後に結果が描かれない原因を、CSS を変えて比べる)。調べ終わったら消す
import { expect, test } from '@playwright/test';

import { mockApi } from './fixtures/api';

const VARIANTS: Record<string, string> = {
  base: '',
  noContentVisibility: '[class*="_paragraph_"]{content-visibility: visible !important}',
  noAutoIntrinsicSize: '[class*="_paragraph_"]{contain-intrinsic-size: 2.1em !important}',
  noIntrinsicSize: '[class*="_paragraph_"]{contain-intrinsic-size: none !important}',
  noClipMargin: '[class*="_paragraph_"]{overflow-clip-margin: 0 !important}',
};

for (const [name, css] of Object.entries(VARIANTS)) {
  test(`diag ${name}`, async ({ page }, testInfo) => {
    await mockApi(page);
    await page.goto('/');
    if (css !== '') {
      await page.addStyleTag({ content: css });
    }
    await page.getByLabel('文章').fill('吾輩は猫である。名前はまだ無い。');
    await page.getByRole('button', { name: '変換する' }).click();
    await page.getByRole('button', { name: '獅子、元の語は猫' }).click();
    await page
      .getByRole('region', { name: /選んだ語/ })
      .getByRole('button', { name: 'この語は置き換えない' })
      .click();
    const token = page.getByRole('button', { name: '猫、置き換えない指定' });
    await token.waitFor({ state: 'attached' });
    await page.waitForTimeout(500);
    const box = await token.boundingBox();
    const visible = await token.isVisible();
    const paragraph = await token.evaluate((el) => {
      const p = el.closest('[class*="_paragraph_"]');
      const r = p?.getBoundingClientRect();
      return { h: r?.height, top: r?.top, vh: window.innerHeight };
    });
    // スクロールして見える位置に出したら描かれるか
    await token.evaluate((el) => {
      el.scrollIntoView({ block: 'center' });
    });
    await page.waitForTimeout(300);
    const visibleAfterScroll = await token.isVisible();
    process.stdout.write(
      `DIAG ${testInfo.project.name} ${name}: visible=${String(visible)} box=${JSON.stringify(box)} paragraph=${JSON.stringify(paragraph)} afterScroll=${String(visibleAfterScroll)}\n`,
    );
    await testInfo.attach(`${name}.png`, {
      body: await page.screenshot(),
      contentType: 'image/png',
    });
    expect(true).toBe(true);
  });
}
