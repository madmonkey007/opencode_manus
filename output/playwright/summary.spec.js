const { test } = require('@playwright/test');

test.setTimeout(60000);

test('summary timing check', async ({ page }) => {
  const URL = 'http://localhost:8089/';
  const PROMPT = '写一个简单的网页版闹钟';

  page.on('console', msg => {
    try {
      console.log(`[console:${msg.type()}] ${msg.text()}`);
    } catch {}
  });

  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  await page.evaluate(() => {
    const target = document.querySelector('#chat-messages') || document.body;
    window.__ocdiag = {
      summaryAt: null,
      mutationsAfterSummary: 0,
      lastMutationAt: null,
      summarySeenCount: 0
    };
    const hasSummary = () => {
      const text = target ? target.innerText || '' : '';
      return text.includes('任务完成');
    };
    const observer = new MutationObserver(() => {
      const now = Date.now();
      window.__ocdiag.lastMutationAt = now;
      if (hasSummary()) {
        if (!window.__ocdiag.summaryAt) {
          window.__ocdiag.summaryAt = now;
          window.__ocdiag.summarySeenCount += 1;
        } else {
          window.__ocdiag.mutationsAfterSummary += 1;
        }
      }
    });
    if (target) {
      observer.observe(target, { childList: true, subtree: true, characterData: true });
    }
    window.__ocdiag_observer = observer;
  });

  if (await page.locator('#prompt').count()) {
    await page.fill('#prompt', PROMPT);
  } else if (await page.locator('#prompt-welcome').count()) {
    await page.fill('#prompt-welcome', PROMPT);
  } else if (await page.locator('textarea').count()) {
    await page.locator('textarea').first().fill(PROMPT);
  }

  if (await page.locator('#runStream').count()) {
    await page.click('#runStream');
  } else if (await page.locator('#runStream-welcome').count()) {
    await page.click('#runStream-welcome');
  } else {
    const btn = page.getByRole('button', { name: '运行' });
    if (await btn.count()) {
      await btn.first().click();
    }
  }

  let summaryFound = false;
  const start = Date.now();
  while (Date.now() - start < 25000) {
    const diag = await page.evaluate(() => window.__ocdiag);
    if (diag && diag.summaryAt) {
      summaryFound = true;
      break;
    }
    await page.waitForTimeout(500);
  }

  await page.waitForTimeout(4000);
  const diag = await page.evaluate(() => window.__ocdiag);

  console.log('SUMMARY_FOUND:', summaryFound);
  console.log('DIAG:', JSON.stringify(diag));
});
