import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DIST_DIR = path.resolve(__dirname, 'dist');
const FILES = ['index.html', 'app.js', 'index.css', 'wake-lock.js', 'favicon.svg'];

fs.rmSync(DIST_DIR, { recursive: true, force: true });
fs.mkdirSync(DIST_DIR, { recursive: true });

for (const file of FILES) {
  const src = path.resolve(__dirname, file);
  if (!fs.existsSync(src)) {
    console.warn(`[build] SKIP (missing): ${file}`);
    continue;
  }
  fs.copyFileSync(src, path.join(DIST_DIR, file));
  console.log(`[build] copied ${file}`);
}

console.log('[build] done');
