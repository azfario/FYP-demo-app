// Exercise the running Docker app using a fresh browser context and actual uploads.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const base = process.env.UI_BASE_URL || 'http://localhost:8081';
const checks = [];
const screenshots = path.join(root, 'docs/screenshots');
const artifacts = path.join(root, 'test-results/ui');
const mark = (name, detail) => { checks.push({ name, detail }); console.log(`PASS ${name}: ${detail}`); };
const visiblePanel = page => page.getByRole('tabpanel', { name: /Segmentation|Hand Test/ });

async function upload(page, folder) {
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    visiblePanel(page).getByRole('button', { name: /^Choose (a|another) folder$/ }).click(),
  ]);
  await chooser.setFiles(folder);
}

async function ready(page) {
  await visiblePanel(page).getByText('Ready to segment.', { exact: true }).waitFor();
}

async function predict(page, hand = false) {
  const response = page.waitForResponse(response => response.url().endsWith(hand ? '/api/hand-test/predict' : '/api/predict') && response.request().method() === 'POST');
  await visiblePanel(page).getByRole('button', { name: /Segment (image|again)/, exact: true }).press('Space');
  const result = await (await response).json();
  await visiblePanel(page).getByText('Segmentation complete.', { exact: true }).waitFor();
  assert.equal(result.width, 512); assert.equal(result.height, 512);
  return result;
}

async function viewsAndDownloads(page, mode) {
  const panel = visiblePanel(page);
  for (const name of ['Optical', 'Radar', 'Mask', 'Overlay']) {
    await panel.getByRole('button', { name, exact: true }).press('Space');
    assert.equal(await panel.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
    assert.match(await panel.locator('.main-image').getAttribute('alt'), new RegExp(name));
  }
  const slider = panel.getByRole('slider', { name: 'Overlay opacity' });
  await slider.press('Home'); assert.equal(await panel.locator('output').innerText(), '0%');
  await slider.press('End'); assert.equal(await panel.locator('output').innerText(), '100%');
  await slider.press('Home');
  for (let i = 0; i < 5; i++) await slider.press('PageUp');
  assert.equal(await panel.locator('.overlay-image').getAttribute('style'), 'opacity: 0.5;');
  await slider.press('Shift+Tab');
  assert.equal(await page.locator(':focus').innerText(), 'Overlay');
  for (const name of ['Mask PNG', 'Overlay PNG', 'Mask GeoTIFF']) {
    const downloaded = page.waitForEvent('download');
    await panel.getByRole('button', { name, exact: true }).click();
    const file = await downloaded;
    await file.saveAs(path.join(artifacts, `${mode}-${file.suggestedFilename()}`));
    assert.equal(await file.failure(), null);
  }
  mark(`${mode} controls`, 'all four views, range Home/End/PageUp, reverse Tab, and three real downloads');
}

async function run() {
  await fs.mkdir(artifacts, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 1200 }, acceptDownloads: true });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base, { waitUntil: 'networkidle' });
    await visiblePanel(page).getByText('4,390,257', { exact: true }).waitFor();
    assert.equal(await visiblePanel(page).getByRole('heading', { name: 'Model computational performance', exact: true }).isVisible(), true);
    assert.equal(await visiblePanel(page).locator('.performance-panel table, .compute-note, .model-name').count(), 0);
    assert.doesNotMatch(await page.locator('body').innerText(), /\bD4\b/);
    assert.equal(await page.title(), 'Flood segmentation · DeepLab');
    assert.equal(await page.getByRole('tab', { name: 'Segmentation', exact: true }).getAttribute('aria-selected'), 'true');
    assert.equal(await visiblePanel(page).getByRole('button', { name: 'Segment image', exact: true }).isDisabled(), true);
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').innerText(), 'Skip to workspace');
    assert.match(await page.locator(':focus').evaluate(e => getComputedStyle(e).outline), /3px/);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'workspace');
    await page.getByRole('tab', { name: 'Segmentation', exact: true }).click();
    await page.screenshot({ path: path.join(screenshots, 'desktop-empty.jpg'), fullPage: true });
    await upload(page, path.join(root, 'sample/bolivia 3')); await ready(page);
    const original = await predict(page);
    assert.equal(original.evaluation, undefined);
    await viewsAndDownloads(page, 'segmentation');
    await page.getByRole('heading', { name: 'Flood Segmentation', exact: true }).click();
    await page.screenshot({ path: path.join(screenshots, 'desktop-results.jpg'), fullPage: true });
    for (const [width, filename] of [[768, 'tablet-results.jpg'], [390, 'mobile-results.jpg']]) {
      await page.setViewportSize({ width, height: 1024 });
      await page.getByRole('heading', { name: 'Flood Segmentation', exact: true }).click();
      const size = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
      assert.equal(size.client, size.scroll);
      await visiblePanel(page).getByRole('button', { name: 'Radar', exact: true }).click();
      await visiblePanel(page).getByRole('button', { name: 'Overlay', exact: true }).click();
      await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
    }
    await page.setViewportSize({ width: 1280, height: 1200 });
    mark('Original workflow', 'pair upload, 512px prediction, no evaluation response, downloads and computational metrics only');

    await page.getByRole('tab', { name: 'Segmentation', exact: true }).focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.getByRole('tab', { name: 'Hand Test', exact: true }).getAttribute('aria-selected'), 'true');
    await upload(page, path.join(root, 'hand test/hand test 1')); await ready(page);
    assert.equal(await visiblePanel(page).locator('.comparison-image').count(), 1);
    assert.equal(await visiblePanel(page).getByText('Click Segment image to show the prediction.', { exact: true }).isVisible(), true);
    mark('Hand Test preview', 'all three filenames shown; only ground truth displayed before Segment');

    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route('**/api/hand-test/predict', async route => { await gate; await route.continue(); });
    const pendingResponse = page.waitForResponse(response => response.url().endsWith('/api/hand-test/predict'));
    pendingResponse.catch(() => {});
    await visiblePanel(page).getByRole('button', { name: 'Segment image', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('tab-hand-test').disabled);
    assert.equal(await page.getByRole('tab', { name: 'Hand Test', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('tab', { name: 'Segmentation', exact: true }).isDisabled(), true);
    assert.equal(await visiblePanel(page).locator('.results-panel').getAttribute('aria-busy'), 'true');
    release();
    const measured = await (await pendingResponse).json();
    await visiblePanel(page).getByText('Segmentation complete.', { exact: true }).waitFor();
    await page.unroute('**/api/hand-test/predict');
    assert.equal(await visiblePanel(page).locator('.comparison-image').count(), 2);
    assert.equal(await visiblePanel(page).getByText('DeepLab prediction', { exact: true }).isVisible(), true);
    assert.equal(await visiblePanel(page).locator('.performance-panel table, .compute-note, .model-name').count(), 0);
    const expected = ['iou', 'dice', 'pixel_accuracy'].map(key => `${(measured.evaluation[key] * 100).toFixed(2)}%`);
    assert.deepEqual(await visiblePanel(page).locator('.evaluation-metrics dd').allTextContents(), expected);
    assert.equal(await page.locator(':focus').getAttribute('id'), 'hand-test-viewer-title');
    mark('Comparison and scores', JSON.stringify(measured.evaluation));
    await predict(page, true);
    await viewsAndDownloads(page, 'hand-test');
    await visiblePanel(page).getByRole('button', { name: 'Compare', exact: true }).click();

    await page.getByRole('tab', { name: 'Hand Test', exact: true }).press('ArrowLeft');
    assert.equal(await visiblePanel(page).getByText('Bolivia_195474', { exact: true }).isVisible(), true);
    assert.equal(await visiblePanel(page).locator('.evaluation-panel').count(), 0);
    await page.getByRole('tab', { name: 'Segmentation', exact: true }).press('End');
    assert.equal(await visiblePanel(page).locator('.comparison-image').count(), 2);
    mark('Tab state', 'independent completed results retained; arrow/Home/End navigation; switching blocked while processing');

    for (const [width, height, filename] of [[1280, 1280, 'hand-test-desktop.jpg'], [768, 1280, 'hand-test-tablet.jpg'], [390, 844, 'hand-test-mobile.jpg'], [320, 768, null]]) {
      await page.setViewportSize({ width, height });
      await page.getByRole('heading', { name: 'Flood Segmentation', exact: true }).click();
      const dimensions = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
      assert.equal(dimensions.client, dimensions.scroll);
      const layout = await visiblePanel(page).locator('.comparison-grid').evaluate(e => getComputedStyle(e).gridTemplateColumns.split(' ').length);
      assert.equal(layout, width <= 700 ? 1 : 2);
      const targets = await page.locator('button:visible:not(:disabled)').evaluateAll(elements => elements.map(e => e.getBoundingClientRect().height));
      assert.ok(targets.every(height => height >= 44));
      if (filename) await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
      mark(`Responsive ${width}`, `no overflow; ${layout} comparison columns; 44px minimum buttons`);
    }

    await upload(page, path.join(root, 'hand test/hand test 2')); await ready(page);
    assert.equal(await visiblePanel(page).locator('.evaluation-panel').count(), 0);
    assert.equal(await visiblePanel(page).locator('.comparison-image').count(), 1);
    await visiblePanel(page).getByRole('button', { name: 'Clear selected images' }).click();
    assert.equal(await visiblePanel(page).locator('img').count(), 0);
    assert.equal(await visiblePanel(page).getByText('Awaiting run', { exact: true }).count(), 2);
    await upload(page, path.join(root, 'sample/bolivia 3'));
    assert.match(await visiblePanel(page).getByRole('alert').innerText(), /exactly three TIFFs/);
    const corruptFolder = path.join(artifacts, 'corrupt'); await fs.mkdir(corruptFolder, { recursive: true });
    for (const name of ['India_900498_S1Hand.tif', 'India_900498_S2Hand.tif']) await fs.copyFile(path.join(root, 'hand test/hand test 1', name), path.join(corruptFolder, name));
    await fs.writeFile(path.join(corruptFolder, 'India_900498_LabelHand.tif'), 'not a tiff');
    await upload(page, corruptFolder);
    await visiblePanel(page).getByRole('alert').waitFor();
    assert.match(await visiblePanel(page).getByRole('alert').innerText(), /Cannot decode ground truth/);
    assert.equal(await visiblePanel(page).getByRole('button', { name: 'Segment image', exact: true }).isDisabled(), true);
    await visiblePanel(page).getByRole('button', { name: 'Clear selected images' }).click();
    mark('Reset and errors', 're-upload removes stale scores, Clear resets timings, missing-label and corrupt-label errors recover');

    await page.route('**/api/model-info', route => route.abort());
    await page.reload({ waitUntil: 'networkidle' });
    await visiblePanel(page).getByRole('button', { name: 'Retry connection', exact: true }).waitFor();
    assert.equal(await visiblePanel(page).getByText('Unavailable', { exact: true }).count(), 2);
    await page.unroute('**/api/model-info');
    await visiblePanel(page).getByRole('button', { name: 'Retry connection', exact: true }).click();
    await visiblePanel(page).getByText('4,390,257', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    mark('Service recovery', 'offline facts unavailable; Retry restores actual model; no uncaught page errors');
    await fs.writeFile(path.join(artifacts, 'report.json'), JSON.stringify(checks, null, 2));
  } finally { await browser.close(); }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
