// Verify the deployed single workspace with real uploads and predictions.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const base = process.env.UI_BASE_URL || 'http://localhost:8081';
const screenshots = path.join(root, 'docs/screenshots');
const artifacts = path.join(root, 'test-results/ui');

async function upload(page, folder) {
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: /^Choose (a|another) folder$/ }).click();
  await (await chooser).setFiles(folder);
}

async function ready(page) {
  await page.getByText('Ready to segment.', { exact: true }).waitFor();
}

async function run() {
  await fs.mkdir(artifacts, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1200 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base, { waitUntil: 'networkidle' });
    await page.getByText('1,401,250', { exact: true }).waitFor();
    assert.equal(await page.getByRole('tab').count(), 0);
    assert.equal(await page.locator('.workspace-grid').count(), 1);
    assert.equal(await page.getByRole('button', { name: 'Segment image', exact: true }).isDisabled(), true);
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').innerText(), 'Skip to workspace');
    assert.match(await page.locator(':focus').evaluate(e => getComputedStyle(e).outline), /3px/);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'workspace');
    await page.screenshot({ path: path.join(screenshots, 'desktop-empty.jpg'), fullPage: true });

    await upload(page, path.join(root, 'sample/bolivia 3'));
    assert.match(await page.getByRole('alert').innerText(), /exactly three TIFFs/);
    assert.equal(await page.getByRole('button', { name: 'Segment image', exact: true }).isDisabled(), true);
    await upload(page, path.join(root, 'hand test/hand test 1'));
    await ready(page);
    assert.equal(await page.locator('.filename').count(), 3);
    assert.equal(await page.locator('.comparison-image').count(), 1);
    assert.equal(await page.getByText('Click Segment image to show the prediction.', { exact: true }).isVisible(), true);
    console.log('PASS single workspace, missing-mask rejection, triplet preview and keyboard entry');

    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route('**/api/hand-test/predict', async route => { await gate; await route.continue(); });
    const response = page.waitForResponse(r => r.url().endsWith('/api/hand-test/predict'));
    await page.getByRole('button', { name: 'Segment image', exact: true }).press('Space');
    await page.getByRole('button', { name: 'Segmenting…', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Segmenting…', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Choose another folder', exact: true }).isDisabled(), true);
    release();
    const result = await (await response).json();
    await page.getByText('Segmentation complete.', { exact: true }).waitFor();
    await page.unroute('**/api/hand-test/predict');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'viewer-title');
    assert.equal(await page.getByRole('button', { name: 'Compare', exact: true }).getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('.comparison-image').count(), 2);
    assert.equal(result.width, 512);
    assert.equal(result.height, 512);
    assert.deepEqual(await page.locator('.evaluation-metrics dd').allTextContents(),
      ['iou', 'dice', 'pixel_accuracy'].map(key => (result.evaluation[key] * 100).toFixed(2) + '%'));
    assert.ok(result.inference_ms > 0 && result.processing_ms > 0);
    console.log('PASS actual prediction, measured scores, timings and processing lock');

    for (const name of ['Optical', 'Radar', 'Permanent water vs flood', 'JRC reference', 'Compare']) {
      await page.getByRole('button', { name, exact: true }).press('Space');
      assert.equal(await page.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
      if (name !== 'Compare') assert.match(await page.locator('.main-image').getAttribute('alt'), new RegExp(name));
    }
    for (const name of ['Permanent water vs flood PNG', 'Permanent water vs flood GeoTIFF', 'Candidate flood GeoTIFF']) {
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name, exact: true }).click();
      const file = await download;
      await file.saveAs(path.join(artifacts, file.suggestedFilename()));
      assert.equal(await file.failure(), null);
    }
    console.log('PASS all five views and three actual downloads');

    for (const [width, filename] of [[1280, 'hand-test-desktop.jpg'], [768, 'hand-test-tablet.jpg'], [390, 'hand-test-mobile.jpg'], [320, null]]) {
      await page.setViewportSize({ width, height: 1000 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth === document.documentElement.clientWidth), true);
      const columns = await page.locator('.comparison-grid').evaluate(e => getComputedStyle(e).gridTemplateColumns.split(' ').length);
      assert.equal(columns, width <= 700 ? 1 : 2);
      assert.ok((await page.locator('button:visible').evaluateAll(es => es.map(e => e.getBoundingClientRect().height))).every(h => h >= 44));
      assert.ok((await page.locator('.image-stage').evaluateAll(es => es.map(e => Math.abs(e.getBoundingClientRect().width - e.getBoundingClientRect().height)))).every(d => d < 1));
      if (width <= 700) {
        const positions = await page.evaluate(() => ['.upload-panel', '.results-panel', '.performance-panel'].map(s => document.querySelector(s).getBoundingClientRect().top));
        assert.ok(positions[0] < positions[1] && positions[1] < positions[2]);
      }
      assert.notEqual(await page.locator('.results-panel').evaluate(e => getComputedStyle(e, '::before').clipPath), 'none');
      if (filename) await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
      console.log('PASS responsive layout ' + width);
    }

    await upload(page, path.join(root, 'hand test/hand test 2'));
    await ready(page);
    assert.equal(await page.locator('.evaluation-panel').count(), 0);
    assert.equal(await page.locator('.comparison-image').count(), 1);
    await page.getByRole('button', { name: 'Clear selected images' }).click();
    assert.equal(await page.locator('img').count(), 0);
    assert.equal(await page.getByText('Awaiting run', { exact: true }).count(), 2);
    const corrupt = path.join(artifacts, 'corrupt');
    await fs.mkdir(corrupt, { recursive: true });
    for (const name of ['India_900498_S1Hand.tif', 'India_900498_S2Hand.tif']) await fs.copyFile(path.join(root, 'hand test/hand test 1', name), path.join(corrupt, name));
    await fs.writeFile(path.join(corrupt, 'India_900498_LabelHand.tif'), 'not a tiff');
    await upload(page, corrupt);
    await page.getByRole('alert').waitFor();
    assert.match(await page.getByRole('alert').innerText(), /Cannot decode ground truth/);
    assert.equal(await page.getByRole('button', { name: 'Segment image', exact: true }).isDisabled(), true);
    console.log('PASS clear, re-upload, stale-score removal and corrupt-mask error');

    await page.route('**/api/model-info', route => route.abort());
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Retry connection', exact: true }).waitFor();
    await page.unroute('**/api/model-info');
    await page.getByRole('button', { name: 'Retry connection', exact: true }).click();
    await page.getByText('1,401,250', { exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log('PASS service retry and no uncaught page errors');
  } finally { await browser.close(); }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
