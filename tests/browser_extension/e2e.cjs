/* Real Chromium extension integration. Run headed under Xvfb on CI. */
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

const token = 'A'.repeat(43);
const received = [];
const html = '<!doctype html><meta charset="utf-8"><textarea id="draft"></textarea>' +
  '<div contenteditable="true" id="rich"></div><input type="password" id="secret">' +
  '<input autocomplete="one-time-code" id="otp"><input aria-label="银行卡号" id="bank">';
const website = http.createServer((_request, response) => {
  response.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'}); response.end(html);
});
const desktop = http.createServer((request, response) => {
  const origin = request.headers.origin || '*';
  response.setHeader('Access-Control-Allow-Origin', origin);
  response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
  if (request.headers.authorization !== `Bearer ${token}`) {
    response.writeHead(403); response.end('{}'); return;
  }
  let body = '';
  request.on('data', data => { body += data; });
  request.on('end', () => {
    if (request.method === 'POST') received.push(JSON.parse(body));
    response.writeHead(200, {'Content-Type': 'application/json'}); response.end('{"ok":true}');
  });
});
async function listen(server, port) {
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
}
async function waitFor(check, what) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await check()) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Timed out: ${what}`);
}
(async () => {
  await listen(website, 0);
  await listen(desktop, 47963);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'clipvault-extension-'));
  let context;
  try {
    const extension = path.resolve(__dirname, '../../browser-extension');
    context = await chromium.launchPersistentContext(profile, {
      ...(process.env.CLIPVAULT_CHROMIUM ? {executablePath:process.env.CLIPVAULT_CHROMIUM} : {channel:'chromium'}),
      headless:false, args:[`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]});
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', {timeout:15000});
    const extensionId = new URL(worker.url()).host;
    const site = `http://127.0.0.1:${website.address().port}`;
    await worker.evaluate(async siteOrigin => {
      await chrome.storage.local.set({config:{enabled:true, sites:[siteOrigin]}});
    }, site);
    const page = await context.newPage();
    await page.goto(site);
    await page.waitForTimeout(400);
    const text = '真实浏览器测试：中文与 English\n第二行 😃';
    await page.locator('#draft').fill(text);
    const rows = async () => worker.evaluate(async () => (await chrome.storage.local.get('drafts')).drafts || []);
    await waitFor(async () => (await rows()).some(item => item.text === text), 'textarea backup');
    await page.locator('#rich').fill('编辑器内容');
    await waitFor(async () => (await rows()).some(item => item.text === '编辑器内容'), 'contenteditable backup');
    await page.locator('#secret').fill('private-pass');
    await page.locator('#otp').fill('123456');
    await page.locator('#bank').fill('98765432101234');
    await page.waitForTimeout(800);
    assert(!(await rows()).some(item => /private-pass|123456|98765432101234/.test(item.text)));
    await page.reload();
    assert((await rows()).some(item => item.text === text), 'backup survives page reload');
    const popup = await context.newPage();
    await popup.goto(`chrome-extension://${extensionId}/popup.html`);
    await popup.locator('.connection summary').click();
    await popup.locator('#token').fill(token);
    await popup.locator('#pair').click();
    await waitFor(async () => (await popup.locator('#pair-message').textContent()).includes('连接成功'), 'desktop pairing');
    await waitFor(() => received.some(item => item.text === text), 'local desktop sync');
    assert(received.every(item => item.origin === site && item.path === '/'));
    assert((await popup.locator('#drafts').textContent()).includes(text.slice(0,15)), 'popup lists saved drafts');
    console.log('Chromium extension capture, reload, privacy and desktop pairing passed.');
  } finally {
    if (context) await context.close();
    await Promise.all([new Promise(resolve => website.close(resolve)),new Promise(resolve => desktop.close(resolve))]);
    fs.rmSync(profile, {recursive:true, force:true});
  }
})().catch(error => { console.error(error); process.exitCode=1; });
