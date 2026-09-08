#!/usr/bin/env node
// Recover exact Vite/Rollup PNG assets embedded in RevolutionMacro.exe.
// Usage: node recover-vite-pngs.js <RevolutionMacro.exe> <www-dir> <rollup-native-js>
const fs = require('fs');
const path = require('path');

const [exePath, wwwDir, rollupNativePath] = process.argv.slice(2);
if (!exePath || !wwwDir || !rollupNativePath) {
  console.error('usage: node recover-vite-pngs.js <exe> <www-dir> <rollup-native-js>');
  process.exit(2);
}
const { xxhashBase64Url } = require(rollupNativePath);
const exe = fs.readFileSync(exePath);
const assetsDir = path.join(wwwDir, 'assets');
const jsFiles = fs.readdirSync(assetsDir).filter(x => x.endsWith('.js'));
const refs = new Set();
for (const file of jsFiles) {
  const text = fs.readFileSync(path.join(assetsDir, file), 'utf8');
  for (const m of text.matchAll(/\/assets\/([A-Za-z0-9_-]+\.png)/g)) refs.add(m[1]);
}

function carvePngs(buf) {
  const sig = Buffer.from([137,80,78,71,13,10,26,10]);
  const out = [];
  let pos = 0;
  while ((pos = buf.indexOf(sig, pos)) >= 0) {
    let p = pos + 8;
    let ok = false;
    while (p + 12 <= buf.length) {
      const len = buf.readUInt32BE(p);
      const typ = buf.toString('ascii', p + 4, p + 8);
      const end = p + 12 + len;
      if (end > buf.length) break;
      p = end;
      if (typ === 'IEND') { ok = true; break; }
    }
    if (ok) {
      out.push({ start: pos, data: buf.subarray(pos, p) });
      pos = p;
    } else {
      pos += 8;
    }
  }
  return out;
}

const pngs = carvePngs(exe);
const byHash = new Map();
for (const png of pngs) {
  const hash = xxhashBase64Url(png.data).slice(0, 8);
  if (!byHash.has(hash)) byHash.set(hash, []);
  byHash.get(hash).push(png);
}

fs.mkdirSync(assetsDir, { recursive: true });
let matched = 0;
const missing = [];
for (const name of [...refs].sort()) {
  const hash = name.slice(-12, -4);
  const hits = byHash.get(hash) || [];
  if (hits.length !== 1) {
    missing.push(`${name} (${hash}) hits=${hits.length}`);
    continue;
  }
  fs.writeFileSync(path.join(assetsDir, name), hits[0].data);
  matched++;
}

console.log(`Revo PNG recovery: refs=${refs.size} carved=${pngs.length} matched=${matched}`);
if (missing.length) {
  console.error('Unresolved PNGs:\n' + missing.join('\n'));
  process.exit(1);
}
if (matched !== refs.size || matched < 100) {
  console.error('PNG recovery did not satisfy all frontend references');
  process.exit(1);
}
