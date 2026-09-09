// Build example first: mkdocs build -f example/mkdocs.yml --strict
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const http = require('node:http');

(async () => {
  const site = path.resolve(__dirname, '../example/site');
  const server = http.createServer(async (req, res) => {
    try {
      const name = new URL(req.url, 'http://localhost').pathname;
      const file = path.resolve(site, '.' + (name === '/' ? '/index.html' : name));
      if (!file.startsWith(site + path.sep)) throw new Error('Invalid path');
      const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' };
      res.setHeader('Content-Type', types[path.extname(file)] ?? 'application/octet-stream');
      res.end(await fs.readFile(file));
    } catch { res.writeHead(404); res.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // Optional local copy of the exact upstream Mermaid asset, for offline tests.
    if (process.env.MERMAID_TEST_SCRIPT) {
      await page.route('**/mermaid.min.js', route => route.fulfill({ path: process.env.MERMAID_TEST_SCRIPT, contentType: 'application/javascript' }));
    }
    const url = `http://127.0.0.1:${server.address().port}/`;
    await page.goto(url);
    await page.waitForFunction(() => document.querySelectorAll('.flow-player svg').length === 2);
    await page.waitForFunction(() => [...document.querySelectorAll('[data-action="next"]')].every(b => !b.disabled));
    const offline = page.locator('[data-flow-id="target-offline"]');
    for (let i = 0; i < 7; i++) await offline.locator('[data-action="next"]').click();
    const target = offline.locator('g.node').filter({ hasText: 'Target PostgreSQL' });
    assert.match(await target.getAttribute('class'), /flow-state-success/);
    assert.doesNotMatch(await target.getAttribute('class'), /flow-state-error/);
    const stroke = await target.locator(':scope > *').first().evaluate(e => getComputedStyle(e).stroke);
    assert.equal(stroke, 'rgb(22, 163, 74)');
    await offline.locator('[data-action="previous"]').click();
    assert.match(await target.getAttribute('class'), /flow-state-error/);
    await offline.locator('[data-action="reset"]').click();
    assert.equal(await offline.locator('.flow-player__counter').textContent(), 'Ready');

    const normal = page.locator('[data-flow-id="normal-replication"]');
    await normal.locator('[data-action="play"]').click();
    await page.waitForFunction(() => document.querySelector('[data-flow-id="normal-replication"] .flow-traveller') !== null);
    await normal.locator('[data-action="play"]').click();
    const marker = normal.locator('.flow-traveller');
    const position = await marker.getAttribute('cx');
    const step = await normal.locator('.flow-player__counter').textContent();
    await page.waitForTimeout(250);
    assert.equal(await marker.getAttribute('cx'), position);
    assert.equal(await normal.locator('.flow-player__counter').textContent(), step);
    await normal.locator('[data-action="play"]').click();
    assert.equal(await normal.locator('.flow-player__counter').textContent(), step);
    await page.waitForFunction(old => {
      const m = document.querySelector('[data-flow-id="normal-replication"] .flow-traveller');
      return !m || m.getAttribute('cx') !== old;
    }, position);
    await normal.locator('[data-action="reset"]').click();
    assert.equal(await normal.locator('.flow-traveller').count(), 0);

    // Insert malformed legacy containers before a valid player and reload scripts.
    await page.route(url, async route => {
      const html = await fs.readFile(path.join(site, 'index.html'), 'utf8');
      const invalid = '<div class="flow-player flow-player--invalid">Warning</div>'
        + '<div class="flow-player"><script class="flow-player__scenario" type="application/json">{broken</script></div>';
      await route.fulfill({ body: html.replace('<div class="flow-player"', invalid + '<div class="flow-player"'), contentType: 'text/html' });
    });
    await page.goto(url);
    await page.waitForFunction(() => document.querySelectorAll('.flow-player svg').length === 2);
    await page.waitForFunction(() => [...document.querySelectorAll('[data-flow-id] [data-action="next"]')].every(b => !b.disabled));
    assert.deepEqual(errors, []);
    console.log('Browser smoke passed: actual Mermaid render, recovery, Previous/Reset, Pause/Resume, invalid-player isolation.');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
