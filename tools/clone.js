#!/usr/bin/env node
// Usage: node tools/clone.js <url> [--screenshot] [--deep]
//
// --deep     Full functional clone: rendered DOM, all API calls/responses,
//            HAR archive, mock server, framework detection, JS bundles.
//            Requires Playwright (npx playwright install chromium).

const { execSync, spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');
const { URL } = require('url');
const os   = require('os');

const IS_WINDOWS = os.platform() === 'win32';

function hasCommand(cmd) {
  const r = spawnSync(IS_WINDOWS ? 'where' : 'which', [cmd], { stdio: 'pipe' });
  return r.status === 0;
}

// Pure Node.js recursive site downloader — used when wget is not available
async function nodeCrawl(startUrl, destDir, maxPages = 200) {
  const base    = new URL(startUrl);
  const visited = new Set();
  const queue   = [startUrl];
  let   count   = 0;

  const ASSET_EXTS = /\.(css|js|png|jpg|jpeg|gif|svg|webp|ico|woff|woff2|ttf|eot|json|xml|txt)(\?.*)?$/i;

  async function fetchSave(url) {
    if (visited.has(url)) return '';
    visited.add(url);
    try {
      const res = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; SiteCloneTool/1.0)' },
        redirect: 'follow',
        signal: AbortSignal.timeout(15_000),
      });
      if (!res.ok) return '';
      const buf = Buffer.from(await res.arrayBuffer());

      // build local path
      const u        = new URL(url);
      let   relPath  = u.pathname.replace(/^\//, '') || 'index.html';
      if (!path.extname(relPath) || relPath.endsWith('/'))
        relPath = relPath.replace(/\/?$/, '/index.html');
      const localPath = path.join(destDir, relPath.split('/').join(path.sep));
      fs.mkdirSync(path.dirname(localPath), { recursive: true });
      fs.writeFileSync(localPath, buf);
      return buf.toString('utf8');
    } catch { return ''; }
  }

  while (queue.length && count < maxPages) {
    const url = queue.shift();
    if (visited.has(url)) continue;
    count++;
    process.stdout.write(`\r  Fetched ${count} pages…`);

    const body = await fetchSave(url);
    if (!body) continue;

    // extract links from HTML
    const linkRe = /(?:href|src|action)=["']([^"'#?]+)/g;
    let m;
    while ((m = linkRe.exec(body))) {
      try {
        const abs = new URL(m[1], url).href;
        if (!abs.startsWith(base.origin)) continue;
        if (visited.has(abs)) continue;
        if (ASSET_EXTS.test(abs)) {
          // assets: fetch immediately, don't recurse
          visited.add(abs);
          fetchSave(abs);
        } else {
          queue.push(abs);
        }
      } catch {}
    }

    // extract asset URLs from CSS
    const cssRe = /url\(["']?([^"')]+)["']?\)/g;
    while ((m = cssRe.exec(body))) {
      try {
        const abs = new URL(m[1], url).href;
        if (abs.startsWith(base.origin) && !visited.has(abs)) {
          visited.add(abs);
          fetchSave(abs);
        }
      } catch {}
    }
  }
  process.stdout.write('\n');
  return count;
}

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const GREEN  = '\x1b[32m';
const CYAN   = '\x1b[36m';
const YELLOW = '\x1b[33m';
const RED    = '\x1b[31m';

const log  = (step, msg) => console.log(`${BOLD}${CYAN}[${step}]${RESET} ${msg}`);
const ok   = msg => console.log(`${GREEN}✓${RESET} ${msg}`);
const warn = msg => console.log(`${YELLOW}⚠${RESET}  ${msg}`);
const err  = msg => console.log(`${RED}✗${RESET}  ${msg}`);

// ── helpers ────────────────────────────────────────────────────────────────

function findFiles(dir, ...exts) {
  if (!fs.existsSync(dir)) return [];
  const results = [];
  const walk = d => {
    try {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const full = path.join(d, e.name);
        if (e.isDirectory()) walk(full);
        else if (exts.some(x => e.name.endsWith(x))) results.push(full);
      }
    } catch {}
  };
  walk(dir);
  return results;
}

function normaliseColor(raw) {
  raw = raw.trim().toLowerCase();
  if (/^#[0-9a-f]{3}$/.test(raw))
    return '#' + raw[1]+raw[1]+raw[2]+raw[2]+raw[3]+raw[3];
  return raw;
}

function extractBrand(filesDir) {
  const colors = new Set();
  const fonts  = new Set();

  const processCSS = content => {
    const colorRe = /(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))/g;
    let m;
    while ((m = colorRe.exec(content))) colors.add(normaliseColor(m[1]));
    const fontRe = /font-family\s*:\s*([^;{}]+)/g;
    while ((m = fontRe.exec(content))) {
      m[1].trim().replace(/!important/i,'').split(',')
        .forEach(f => { const c = f.trim().replace(/['"]/g,'').trim(); if (c) fonts.add(c); });
    }
    const gfRe = /https?:\/\/fonts\.googleapis\.com\/css[^\s'")\]]+/g;
    while ((m = gfRe.exec(content))) fonts.add(`(Google Font) ${m[0]}`);
  };

  findFiles(filesDir, '.css').forEach(f => processCSS(fs.readFileSync(f, 'utf8')));
  findFiles(filesDir, '.html').forEach(f => {
    const c = fs.readFileSync(f, 'utf8');
    const re = /style=["']([^"']+)["']/g;
    let m;
    while ((m = re.exec(c))) processCSS(m[1]);
  });

  const cleanColors = [...colors].filter(c =>
    c.startsWith('#') || c.startsWith('rgb') || c.startsWith('hsl')
  );
  return { colors: cleanColors, fonts: [...fonts] };
}

// detect which JS framework is running on the page
function detectFramework(html, jsContent) {
  const clues = {
    'React':      [/__reactFiber|__reactProps|react\.production\.min|ReactDOM/],
    'Next.js':    [/__NEXT_DATA__|next\/dist/],
    'Vue 3':      [/__vue__|createApp\(|defineComponent/],
    'Vue 2':      [/new Vue\(|Vue\.component|vue\.runtime/],
    'Nuxt':       [/__NUXT__|nuxtApp/],
    'Angular':    [/ng-version|ngIf|angular\.min|zone\.js/],
    'Svelte':     [/__svelte|SvelteComponent/],
    'Astro':      [/astro-island|astro\.config/],
    'jQuery':     [/jquery\.min\.js|jQuery\.fn|window\.\$/],
    'Alpine.js':  [/x-data=|x-bind:|alpine\.js/],
    'HTMX':       [/hx-get=|hx-post=|htmx\.js/],
    'Ember':      [/Ember\.Application|ember\.js/],
    'Backbone':   [/Backbone\.Model|backbone\.js/],
  };
  const combined = html + (jsContent || '');
  const detected = [];
  for (const [name, patterns] of Object.entries(clues)) {
    if (patterns.some(p => p.test(combined))) detected.push(name);
  }
  return detected;
}

// generate a standalone Express mock server from intercepted requests
function buildMockServer(outDir, requests, origin) {
  if (!requests.length) return null;

  const routes = requests
    .filter(r => r.method !== 'OPTIONS' && r.responseBody !== undefined)
    .map(r => {
      const url = new URL(r.url);
      const routePath = url.pathname + (url.search || '');
      const body = typeof r.responseBody === 'string'
        ? JSON.stringify(r.responseBody)
        : JSON.stringify(JSON.stringify(r.responseBody));
      return `
  app.${r.method.toLowerCase()}(${JSON.stringify(routePath)}, (req, res) => {
    res.set('Content-Type', ${JSON.stringify(r.contentType || 'application/json')});
    res.set('Access-Control-Allow-Origin', '*');
    res.status(${r.status || 200}).send(${body});
  });`;
    }).join('\n');

  const server = `// Auto-generated mock server for ${origin}
// Run: npm install express && node mock-server.js
const express = require('express');
const path    = require('path');
const app     = express();

// serve the cloned frontend
app.use(express.static(path.join(__dirname, 'files')));

// replayed API responses
${routes}

app.listen(3000, () => console.log('Mock server running at http://localhost:3000'));
`;

  const outPath = path.join(outDir, 'mock-server.js');
  fs.writeFileSync(outPath, server);
  return outPath;
}

// ── deep capture via Playwright ────────────────────────────────────────────

async function deepCapture(targetUrl, outDir) {
  let playwright;
  try {
    playwright = require('playwright');
  } catch {
    err('Playwright not found. Run: npm install playwright && npx playwright install chromium');
    return null;
  }

  const { chromium } = playwright;
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordHar: { path: path.join(outDir, 'archive.har'), mode: 'full' },
  });
  const page = await context.newPage();

  const intercepted = [];

  // intercept every network request + response
  page.on('response', async response => {
    const req = response.request();
    const url = req.url();
    if (url.startsWith('data:') || url.startsWith('blob:')) return;

    let responseBody;
    const ct = response.headers()['content-type'] || '';
    try {
      if (ct.includes('application/json')) {
        responseBody = await response.json();
      } else if (ct.includes('text/')) {
        responseBody = await response.text();
      }
    } catch {}

    intercepted.push({
      method:       req.method(),
      url,
      status:       response.status(),
      contentType:  ct,
      requestHeaders:  req.headers(),
      responseBody,
    });
  });

  console.log('  Navigating…');
  await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 60_000 });

  // wait a moment for deferred JS to run
  await page.waitForTimeout(2000);

  // capture rendered DOM (what you see in DevTools — post-JS)
  const renderedHTML = await page.content();
  fs.writeFileSync(path.join(outDir, 'rendered.html'), renderedHTML);
  ok('Rendered DOM saved (post-JS execution).');

  // screenshots
  await page.screenshot({ path: path.join(outDir, 'screenshot-full.png'), fullPage: true });
  await page.screenshot({ path: path.join(outDir, 'screenshot-viewport.png') });
  ok('Screenshots saved.');

  // local storage + cookies
  const storage = await page.evaluate(() => ({
    localStorage:  { ...window.localStorage },
    sessionStorage: { ...window.sessionStorage },
  }));
  const cookies = await context.cookies();
  fs.writeFileSync(path.join(outDir, 'storage.json'), JSON.stringify({ storage, cookies }, null, 2));

  // console errors / warnings (can reveal hidden functionality)
  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push({ type: msg.type(), text: msg.text() }));

  await context.close();
  await browser.close();

  // save HAR is automatic via recordHar option above
  ok(`HAR archive saved (${intercepted.length} requests captured).`);

  // api-focused requests only
  const origin = new URL(targetUrl).origin;
  const apiCalls = intercepted.filter(r => {
    const u = r.url;
    return (r.contentType || '').includes('json') ||
           u.includes('/api/') || u.includes('/graphql') ||
           u.includes('/v1/') || u.includes('/v2/') ||
           u.includes('/rest/');
  });

  fs.writeFileSync(
    path.join(outDir, 'api-map.json'),
    JSON.stringify(apiCalls.map(r => ({
      method: r.method, url: r.url, status: r.status,
      contentType: r.contentType, response: r.responseBody,
    })), null, 2)
  );
  ok(`API map saved (${apiCalls.length} API calls found).`);

  // detect framework from rendered HTML + first JS bundle
  const jsBundles = findFiles(path.join(outDir, 'files'), '.js');
  let jsSample = '';
  if (jsBundles.length) {
    try { jsSample = fs.readFileSync(jsBundles[0], 'utf8').slice(0, 50_000); } catch {}
  }
  const frameworks = detectFramework(renderedHTML, jsSample);
  ok(`Framework detection: ${frameworks.length ? frameworks.join(', ') : 'none detected / vanilla JS'}`);

  // generate mock server
  const mockPath = buildMockServer(outDir, intercepted, origin);
  if (mockPath) ok('Mock server generated → mock-server.js');

  fs.writeFileSync(
    path.join(outDir, 'console-logs.json'),
    JSON.stringify(consoleLogs, null, 2)
  );

  return { frameworks, intercepted, apiCalls };
}

// ── main ──────────────────────────────────────────────────────────────────

async function cloneSite(targetUrl, opts) {
  const { wantScreenshot, deepMode } = opts;
  const parsed  = new URL(targetUrl);
  const domain  = parsed.hostname;
  const outDir  = path.resolve(`./cloned/${domain}-${Date.now()}`);
  const filesDir = path.join(outDir, 'files');
  fs.mkdirSync(filesDir, { recursive: true });

  console.log(`\n${BOLD}Site Clone Tool${deepMode ? ' (deep mode)' : ''}${RESET}`);
  console.log(`Target : ${targetUrl}`);
  console.log(`Output : ${outDir}\n`);

  // ── 1: download all static files ────────────────────────────────────
  log('1/5', 'Downloading all static files…');
  if (hasCommand('wget')) {
    try {
      execSync(
        `wget --mirror --convert-links --adjust-extension --page-requisites ` +
        `--no-parent --quiet -P "${filesDir}" "${targetUrl}"`,
        { stdio: 'inherit', timeout: 120_000 }
      );
      ok('Files downloaded (wget).');
    } catch {
      warn('wget finished (some external resource errors are normal).');
    }
  } else {
    warn('wget not found — using built-in Node.js crawler (no extra install needed).');
    const n = await nodeCrawl(targetUrl, filesDir);
    ok(`Files downloaded via Node.js crawler (${n} pages).`);
  }

  const cssFiles  = findFiles(filesDir, '.css');
  const htmlFiles = findFiles(filesDir, '.html');
  const jsFiles   = findFiles(filesDir, '.js');
  const imgFiles  = findFiles(filesDir, '.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif');
  ok(`Static assets: ${htmlFiles.length} HTML, ${cssFiles.length} CSS, ${jsFiles.length} JS, ${imgFiles.length} images.`);

  // ── 2: screenshot (lightweight mode) ────────────────────────────────
  let deepResult = null;
  if (deepMode) {
    log('2/5', 'Deep capture: rendered DOM + network interception…');
    deepResult = await deepCapture(targetUrl, outDir);
  } else {
    log('2/5', 'Screenshot…');
    if (wantScreenshot) {
      try {
        const { chromium } = require('playwright');
        const browser = await chromium.launch();
        const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
        await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30_000 });
        await page.screenshot({ path: path.join(outDir, 'screenshot-full.png'), fullPage: true });
        await page.screenshot({ path: path.join(outDir, 'screenshot-viewport.png') });
        await browser.close();
        ok('Screenshots saved.');
      } catch (e) { warn(`Screenshot failed: ${e.message}`); }
    } else {
      warn('Screenshot skipped. Use --screenshot or --deep to capture.');
    }
  }

  // ── 3: extract colors + fonts ────────────────────────────────────────
  log('3/5', 'Extracting brand: colors and fonts…');
  const { colors, fonts } = extractBrand(filesDir);
  ok(`Found ${colors.length} colors, ${fonts.length} font families.`);

  // ── 4: framework + JS analysis ───────────────────────────────────────
  log('4/5', 'Analysing JavaScript and framework…');
  let frameworks = deepResult?.frameworks || [];
  if (!deepResult && (htmlFiles.length || jsFiles.length)) {
    let sample = '';
    try { sample = fs.readFileSync(htmlFiles[0] || jsFiles[0], 'utf8').slice(0, 80_000); } catch {}
    frameworks = detectFramework(sample, '');
    ok(`Framework: ${frameworks.length ? frameworks.join(', ') : 'none detected / vanilla JS'}`);
  }

  // list all <script src> and external JS to give an inventory
  const scriptInventory = [];
  for (const f of htmlFiles) {
    try {
      const html = fs.readFileSync(f, 'utf8');
      const re = /<script[^>]+src=["']([^"']+)["']/g;
      let m;
      while ((m = re.exec(html))) scriptInventory.push(m[1]);
    } catch {}
  }

  // ── 5: generate all outputs ─────────────────────────────────────────
  log('5/5', 'Generating outputs…');

  // CSS custom properties ready to drop into your project
  const cssVars = [
    `/* Brand variables cloned from ${domain} */`,
    `/* Replace values with your own branding */`,
    `:root {`,
    ...colors.slice(0, 20).map((c, i) => `  --color-${i + 1}: ${c};`),
    ...fonts.filter(f => !f.startsWith('(')).slice(0, 5)
            .map((f, i) => `  --font-${i + 1}: "${f}", sans-serif;`),
    `}`,
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'brand-variables.css'), cssVars);

  // full structured report
  const report = {
    url: targetUrl,
    domain,
    clonedAt: new Date().toISOString(),
    deepMode,
    frameworks,
    brand: { colors: colors.slice(0, 60), fonts },
    assets: {
      htmlFiles: htmlFiles.length, cssFiles: cssFiles.length,
      jsFiles: jsFiles.length, imageFiles: imgFiles.length,
      scripts: [...new Set(scriptInventory)],
    },
    ...(deepResult ? {
      apiCalls:    deepResult.apiCalls.length,
      totalRequests: deepResult.intercepted.length,
    } : {}),
  };
  fs.writeFileSync(path.join(outDir, 'brand-report.json'), JSON.stringify(report, null, 2));

  const deepOutputs = deepMode ? `
  rendered.html       — full DOM after JavaScript runs (what DevTools shows)
  archive.har         — complete HTTP archive of every request
  api-map.json        — all API/JSON calls with responses
  mock-server.js      — local Express server replaying all captured responses
  storage.json        — localStorage, sessionStorage, cookies
  console-logs.json   — JS console output` : '';

  const summary = `
SITE CLONE REPORT
=================
URL        : ${targetUrl}
Domain     : ${domain}
Cloned     : ${report.clonedAt}
Mode       : ${deepMode ? 'DEEP (functional)' : 'standard'}
Framework  : ${frameworks.length ? frameworks.join(', ') : 'not detected / vanilla JS'}

FONTS (${fonts.length})
${fonts.map(f => `  • ${f}`).join('\n') || '  (none found)'}

COLORS (${colors.length})
${colors.slice(0, 30).map(c => `  ${c}`).join('\n') || '  (none found)'}

ASSETS
  HTML  : ${htmlFiles.length}
  CSS   : ${cssFiles.length}
  JS    : ${jsFiles.length}
  Images: ${imgFiles.length}
${deepMode && deepResult ? `
API CAPTURE
  Total requests : ${deepResult.intercepted.length}
  API calls      : ${deepResult.apiCalls.length}` : ''}
OUTPUTS
  files/               — full mirrored site (open in browser)
  brand-variables.css  — CSS custom properties for your project
  brand-report.json    — structured analysis${deepOutputs}
`;

  fs.writeFileSync(path.join(outDir, 'SUMMARY.txt'), summary);
  console.log(summary);

  if (deepMode) {
    console.log(`${BOLD}To run the functional clone locally:${RESET}`);
    console.log(`  cd ${outDir}`);
    console.log(`  npm install express`);
    console.log(`  node mock-server.js`);
    console.log(`  open http://localhost:3000\n`);
  }

  ok(`Done → ${outDir}`);
}

// ── entry ─────────────────────────────────────────────────────────────────

const args           = process.argv.slice(2);
const targetUrl      = args.find(a => a.startsWith('http'));
const wantScreenshot = args.includes('--screenshot');
const deepMode       = args.includes('--deep');

if (!targetUrl) {
  console.error(`\nUsage: node tools/clone.js <url> [flags]\n`);
  console.error(`Flags:`);
  console.error(`  --screenshot   Capture full-page PNG  (requires Playwright + Chromium)`);
  console.error(`  --deep         Full functional clone:`);
  console.error(`                   • Rendered DOM (post-JS, not just view-source)`);
  console.error(`                   • Every network request + response intercepted`);
  console.error(`                   • HAR archive`);
  console.error(`                   • API map with all responses`);
  console.error(`                   • Auto-generated mock server`);
  console.error(`                   • Framework detection`);
  console.error(`                   • localStorage / cookies captured\n`);
  console.error(`Examples:`);
  console.error(`  node tools/clone.js https://competitor.com`);
  console.error(`  node tools/clone.js https://competitor.com --screenshot`);
  console.error(`  node tools/clone.js https://competitor.com --deep\n`);
  process.exit(1);
}

cloneSite(targetUrl, { wantScreenshot, deepMode }).catch(e => {
  console.error(RED + 'Fatal: ' + RESET + e.message);
  process.exit(1);
});
