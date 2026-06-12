#!/usr/bin/env node
// Usage: node tools/clone.js <url> [--no-screenshot]

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const RESET = '\x1b[0m';
const BOLD  = '\x1b[1m';
const GREEN = '\x1b[32m';
const CYAN  = '\x1b[36m';
const YELLOW= '\x1b[33m';
const RED   = '\x1b[31m';

function log(step, msg) { console.log(`${BOLD}${CYAN}[${step}]${RESET} ${msg}`); }
function ok(msg)         { console.log(`${GREEN}✓${RESET} ${msg}`); }
function warn(msg)       { console.log(`${YELLOW}⚠${RESET}  ${msg}`); }

// ── helpers ────────────────────────────────────────────────────────────────

function findFiles(dir, ext) {
  if (!fs.existsSync(dir)) return [];
  const results = [];
  const walk = d => {
    try {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const full = path.join(d, e.name);
        if (e.isDirectory()) walk(full);
        else if (e.name.endsWith(ext)) results.push(full);
      }
    } catch {}
  };
  walk(dir);
  return results;
}

// normalise any color to lowercase, collapse short hex → #rrggbb
function normaliseColor(raw) {
  raw = raw.trim().toLowerCase();
  if (/^#[0-9a-f]{3}$/.test(raw)) {
    return '#' + raw[1]+raw[1]+raw[2]+raw[2]+raw[3]+raw[3];
  }
  return raw;
}

function extractFromCSS(content) {
  const colors = new Set();
  const fonts  = new Set();

  // colors: hex, rgb/rgba, hsl/hsla, named used in value position
  const colorRe = /(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))/g;
  let m;
  while ((m = colorRe.exec(content))) colors.add(normaliseColor(m[1]));

  // font-family declarations
  const fontRe = /font-family\s*:\s*([^;{}]+)/g;
  while ((m = fontRe.exec(content))) {
    const raw = m[1].trim().replace(/!important/i, '').trim();
    // split by comma, clean quotes
    raw.split(',').forEach(f => {
      const cleaned = f.trim().replace(/['"]/g, '').trim();
      if (cleaned) fonts.add(cleaned);
    });
  }

  // Google Fonts @import URLs
  const gfRe = /https?:\/\/fonts\.googleapis\.com\/css[^\s'")\]]+/g;
  while ((m = gfRe.exec(content))) fonts.add(`(Google Font) ${m[0]}`);

  return { colors, fonts };
}

function extractFromHTML(content) {
  const colors = new Set();
  const fonts  = new Set();

  // inline styles
  const styleAttr = /style=["']([^"']+)["']/g;
  let m;
  while ((m = styleAttr.exec(content))) {
    const { colors: c, fonts: f } = extractFromCSS(m[1]);
    c.forEach(x => colors.add(x));
    f.forEach(x => fonts.add(x));
  }

  return { colors, fonts };
}

// ── main ──────────────────────────────────────────────────────────────────

async function cloneSite(targetUrl, wantScreenshot) {
  const parsed = new URL(targetUrl);
  const domain = parsed.hostname;
  const outDir = path.resolve(`./cloned/${domain}-${Date.now()}`);
  const filesDir = path.join(outDir, 'files');
  fs.mkdirSync(filesDir, { recursive: true });

  console.log(`\n${BOLD}Site Clone Tool${RESET}`);
  console.log(`Target : ${targetUrl}`);
  console.log(`Output : ${outDir}\n`);

  // ── Step 1: download ──────────────────────────────────────────────────
  log('1/4', 'Downloading full site…');
  try {
    execSync(
      `wget --mirror --convert-links --adjust-extension --page-requisites ` +
      `--no-parent --quiet -P "${filesDir}" "${targetUrl}"`,
      { stdio: 'inherit', timeout: 120_000 }
    );
    ok('Site downloaded.');
  } catch {
    warn('wget finished with some errors (normal for external resources).');
  }

  // ── Step 2: screenshot ────────────────────────────────────────────────
  log('2/4', 'Capturing screenshot…');
  let screenshotPaths = null;
  if (wantScreenshot) {
    try {
      const { chromium } = require('playwright');
      const browser = await chromium.launch();
      const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
      await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30_000 });
      const full = path.join(outDir, 'screenshot-full.png');
      const vp   = path.join(outDir, 'screenshot-viewport.png');
      await page.screenshot({ path: full, fullPage: true });
      await page.screenshot({ path: vp });
      await browser.close();
      screenshotPaths = [full, vp];
      ok('Screenshots saved.');
    } catch (e) {
      warn(`Screenshot skipped: ${e.message}`);
    }
  } else {
    warn('Screenshot skipped (pass --screenshot to enable, requires Chromium).');
  }

  // ── Step 3: extract colors + fonts ────────────────────────────────────
  log('3/4', 'Extracting fonts and colors…');
  const allColors = new Set();
  const allFonts  = new Set();

  for (const f of findFiles(filesDir, '.css')) {
    const { colors, fonts } = extractFromCSS(fs.readFileSync(f, 'utf8'));
    colors.forEach(c => allColors.add(c));
    fonts.forEach(f => allFonts.add(f));
  }
  for (const f of findFiles(filesDir, '.html')) {
    const { colors, fonts } = extractFromHTML(fs.readFileSync(f, 'utf8'));
    colors.forEach(c => allColors.add(c));
    fonts.forEach(f => allFonts.add(f));
  }

  // filter noise: only keep colors that look deliberate
  const cleanColors = [...allColors].filter(c =>
    c.startsWith('#') || c.startsWith('rgb') || c.startsWith('hsl')
  );

  ok(`Found ${cleanColors.length} colors, ${allFonts.size} font families.`);

  // ── Step 4: generate report ───────────────────────────────────────────
  log('4/4', 'Building brand report…');
  const cssFiles  = findFiles(filesDir, '.css');
  const htmlFiles = findFiles(filesDir, '.html');
  const imgFiles  = [
    ...findFiles(filesDir, '.png'),
    ...findFiles(filesDir, '.jpg'),
    ...findFiles(filesDir, '.jpeg'),
    ...findFiles(filesDir, '.svg'),
    ...findFiles(filesDir, '.webp'),
  ];

  const report = {
    url: targetUrl,
    domain,
    clonedAt: new Date().toISOString(),
    screenshots: screenshotPaths,
    brand: {
      colors: cleanColors.slice(0, 60),
      fonts:  [...allFonts],
    },
    assets: {
      cssFiles:   cssFiles.length,
      htmlFiles:  htmlFiles.length,
      imageFiles: imgFiles.length,
      images:     imgFiles.map(f => path.relative(outDir, f)),
    },
  };

  fs.writeFileSync(
    path.join(outDir, 'brand-report.json'),
    JSON.stringify(report, null, 2)
  );

  // human-readable CSS variables file ready to drop into your project
  const cssVars = [
    `/* Brand variables extracted from ${domain} */`,
    `/* Generated by clone.js — replace with your own values */`,
    `:root {`,
    ...cleanColors.slice(0, 20).map((c, i) => `  --color-${i + 1}: ${c};`),
    ...([...allFonts].filter(f => !f.startsWith('(')).slice(0, 5)
        .map((f, i) => `  --font-${i + 1}: "${f}", sans-serif;`)),
    `}`,
  ].join('\n');

  fs.writeFileSync(path.join(outDir, 'brand-variables.css'), cssVars);

  const summary = `
SITE CLONE REPORT
=================
URL     : ${targetUrl}
Domain  : ${domain}
Cloned  : ${report.clonedAt}

FONTS (${allFonts.size})
${[...allFonts].map(f => `  • ${f}`).join('\n') || '  (none found)'}

COLORS (${cleanColors.length})
${cleanColors.slice(0, 30).map(c => `  ${c}`).join('\n') || '  (none found)'}

ASSETS
  CSS files   : ${cssFiles.length}
  HTML files  : ${htmlFiles.length}
  Image files : ${imgFiles.length}

OUTPUTS
  files/            — full mirrored site
  brand-report.json — structured data
  brand-variables.css — ready-to-use CSS custom properties
  ${screenshotPaths ? screenshotPaths.map(p => path.basename(p)).join(', ') : '(no screenshots)'}
`;

  fs.writeFileSync(path.join(outDir, 'SUMMARY.txt'), summary);
  console.log(summary);
  ok(`All done → ${outDir}`);
}

// ── entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const targetUrl = args.find(a => a.startsWith('http'));
const wantScreenshot = args.includes('--screenshot');

if (!targetUrl) {
  console.error(`\nUsage: node tools/clone.js <url> [--screenshot]\n`);
  console.error(`  --screenshot   Capture full-page PNG (requires Chromium)\n`);
  console.error(`Examples:`);
  console.error(`  node tools/clone.js https://example.com`);
  console.error(`  node tools/clone.js https://competitor.com --screenshot\n`);
  process.exit(1);
}

cloneSite(targetUrl, wantScreenshot).catch(err => {
  console.error(RED + 'Error: ' + RESET + err.message);
  process.exit(1);
});
