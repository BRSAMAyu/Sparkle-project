// V4-B04 live-stack admin-face capture. Real local stack, no mocks.
// Channel: web-admin (product mobile/web build broken at this SHA - see build_logs/).
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const OUT = '/Users/brsama/code/GitHub/wtB04/v4/evidence/V4-B04/screenshots';
fs.mkdirSync(OUT, { recursive: true });

const results = [];
function log(r) { results.push(r); console.log(JSON.stringify(r)); }

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-first-run', '--disable-extensions'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: 2 });

  const env = await page.evaluate(() => ({
    userAgent: navigator.userAgent,
    dpr: window.devicePixelRatio,
    lang: navigator.language,
    platform: navigator.platform,
    fontScaleNote: 'browser default (16px root), no text-size override',
  }));
  log({ step: 'env', ...env });

  async function shot(file, clipNote) {
    const p = path.join(OUT, file);
    await page.screenshot({ path: p });
    const b = fs.statSync(p).size;
    log({ step: 'screenshot', file, bytes: b, url: page.url(), note: clipNote || '' });
  }

  // 1. Engine root status
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle0', timeout: 30000 });
  const rootText = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(path.join(OUT, 'fastapi_root_body.txt'), rootText);
  await shot('01_fastapi_root_status.png', 'AI engine root status JSON, live');

  // 2. Swagger UI top
  await page.goto('http://127.0.0.1:8000/docs', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('.opblock', { timeout: 90000 });
  await shot('02_fastapi_docs_top.png', 'Swagger UI top with title+version banner');

  // 3. Expand POST /api/v1/auth/guest panel (overlay/panel content visible check)
  const expanded = await page.evaluate(() => {
    const blocks = [...document.querySelectorAll('.opblock')];
    const target = blocks.find(b => {
      const a = b.querySelector('a.opblock-summary');
      const path = a ? a.querySelector('span.opblock-summary-path') : null;
      return path && path.textContent.trim() === '/api/v1/auth/guest';
    });
    if (!target) return { found: false, totalBlocks: blocks.length };
    const before = target.classList.contains('is-open');
    if (!before) target.querySelector('a.opblock-summary').click();
    return { found: true, totalBlocks: blocks.length, wasOpen: before };
  });
  await new Promise(r => setTimeout(r, 800));
  if (expanded.found) {
    const panelInfo = await page.evaluate(() => {
      const blocks = [...document.querySelectorAll('.opblock')];
      const target = blocks.find(b => {
        const a = b.querySelector('a.opblock-summary');
        const path = a ? a.querySelector('span.opblock-summary-path') : null;
        return path && path.textContent.trim() === '/api/v1/auth/guest';
      });
      const body = target ? target.querySelector('.opblock-body') : null;
      if (!body) return { bodyVisible: false };
      const rect = body.getBoundingClientRect();
      const style = getComputedStyle(body);
      return {
        bodyVisible: rect.height > 40 && style.display !== 'none',
        bodyHeightPx: Math.round(rect.height),
        hasRequestBody: !!body.querySelector('.opblock-section'),
        endpointVisibleText: (body.querySelector('.opblock-description-wrapper, .opblock-summary-description') || {}).textContent || '',
      };
    });
    log({ step: 'panel_expand_check', target: 'POST /api/v1/auth/guest', ...expanded, ...panelInfo });
    // Scroll the panel into view and capture it (top-layer content visible)
    await page.evaluate(() => {
      const blocks = [...document.querySelectorAll('.opblock')];
      const target = blocks.find(b => {
        const a = b.querySelector('a.opblock-summary');
        const path = a ? a.querySelector('span.opblock-summary-path') : null;
        return path && path.textContent.trim() === '/api/v1/auth/guest';
      });
      if (target) target.scrollIntoView({ block: 'start' });
    });
    await new Promise(r => setTimeout(r, 500));
    await shot('03_fastapi_docs_guest_endpoint_expanded.png', 'expanded endpoint panel content visible (overlay-content-visible analog, collapsed capture of same panel would fail this check)');
    // panel scrolled top region with 02 for contrast already captured collapsed-list
  } else {
    log({ step: 'panel_expand_check', found: false });
  }

  // 4. Collapsed-vs-expanded negative control: capture collapsed state of same URL fresh load
  await page.goto('http://127.0.0.1:8000/docs', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('.opblock', { timeout: 90000 });
  const collapsedCheck = await page.evaluate(() => {
    const blocks = [...document.querySelectorAll('.opblock')];
    const target = blocks.find(b => {
      const a = b.querySelector('a.opblock-summary');
      const path = a ? a.querySelector('span.opblock-summary-path') : null;
      return path && path.textContent.trim() === '/api/v1/auth/guest';
    });
    if (!target) return { found: false };
    const body = target.querySelector('.opblock-body');
    return {
      found: true,
      bodyHiddenByDefault: !body || getComputedStyle(body).display === 'none' || body.getBoundingClientRect().height < 5,
    };
  });
  log({ step: 'collapsed_negative_control', ...collapsedCheck, semantics: 'default collapsed capture hides panel content => a baseline capture that only grabs background/summary must FAIL the content-visible check' });

  // 5. Gateway healthz (browser-rendered live JSON)
  await page.goto('http://127.0.0.1:8080/healthz', { waitUntil: 'networkidle0', timeout: 30000 });
  const healthzText = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(path.join(OUT, 'gateway_healthz_body.txt'), healthzText);
  await shot('04_gateway_healthz_live.png', 'gateway healthz JSON, live');

  // 6. Gateway metrics top
  await page.goto('http://127.0.0.1:8080/metrics', { waitUntil: 'networkidle0', timeout: 30000 });
  await shot('05_gateway_metrics_top.png', 'gateway /metrics top, live');
  const metricsText = await page.evaluate(() => document.body.innerText);
  fs.writeFileSync(path.join(OUT, 'gateway_metrics_head200.txt'), metricsText.split('\n').slice(0, 200).join('\n'));

  await browser.close();
  fs.writeFileSync('/tmp/b04_capture/capture_results.json', JSON.stringify(results, null, 2));
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
