// Mencetak blok Baton dari TASKS.md. Dipanggil hook SessionStart (.claude/settings.json),
// sehingga stdout-nya masuk ke konteks setiap sesi Claude Code baru.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tasksPath = path.join(root, 'TASKS.md');

let text;
try {
  text = fs.readFileSync(tasksPath, 'utf8');
} catch {
  console.log('[baton] TASKS.md tidak ditemukan.');
  process.exit(0);
}

const match = text.match(/## Baton saat ini[\s\S]*?```text\r?\n([\s\S]*?)\r?\n```/);
if (!match) {
  console.log('[baton] Blok "Baton saat ini" tidak ditemukan di TASKS.md.');
  process.exit(0);
}

console.log('BATON PROYEK (dari TASKS.md):');
console.log(match[1]);
console.log('');
console.log('Baca CLAUDE.md untuk aturan kerja. Alur task: /mulai <ID> → setujui kontrak → /tutup → /done <ID> (khusus pemilik).');
