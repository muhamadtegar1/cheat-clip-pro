"""Cek konsistensi docs/codemap dengan kode.

Jalankan dari mana saja: venv\\Scripts\\python.exe scripts\\check_codemap.py
Keluar dengan kode 0 bila semua cek lulus, 1 bila ada temuan.

Yang dicek:
1. Setiap link [[nama]] menunjuk ke catatan yang ada.
2. Setiap catatan (selain index) punya link masuk dan ditautkan dari index.
3. Baris tabel `| file | simbol | Lawal-akhir | ... |`:
   - file ada dan rentang tidak melewati panjang file;
   - bila simbol ditulis sebagai `nama` (nama fungsi/kelas/variabel asli), rentangnya harus sama persis
     dengan deklarasi di kode (AST Python atau TypeScript compiler API).
   Simbol tanpa backtick dianggap label potongan dan hanya dicek batasnya.
"""
import ast
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

FILE_CELL = re.compile(r'`([^`]+\.(?:py|tsx?|js|cjs|bat))`')
RANGE_CELL = re.compile(r'L(\d+)(?:-(\d+))?')
SYMBOL_CELL = re.compile(r'`([A-Za-z_][A-Za-z0-9_]*)`')


def load_notes():
    return {os.path.basename(p)[:-3]: open(p, encoding='utf-8').read() for p in glob.glob('docs/codemap/*.md')}


def check_links(notes, errs):
    inbound = {n: set() for n in notes}
    for name, text in notes.items():
        for link in re.findall(r'\[\[([^\]|#]+)', text):
            if link not in notes:
                errs.append(f'{name}: link patah [[{link}]]')
            elif link != name:
                inbound[link].add(name)
    for name, sources in inbound.items():
        if name == 'index':
            continue
        if not sources:
            errs.append(f'{name}: catatan yatim (tanpa link masuk)')
        elif 'index' not in sources:
            errs.append(f'{name}: tidak ditautkan dari index')


def table_rows(notes):
    rows = []
    for name, text in notes.items():
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) < 3:
                continue
            fm, rm = FILE_CELL.fullmatch(cells[0]), RANGE_CELL.fullmatch(cells[2])
            if fm and rm:
                start = int(rm.group(1))
                rows.append((name, fm.group(1), cells[1], start, int(rm.group(2) or start)))
    return rows


def python_symbols(path, cache):
    if path not in cache:
        tree = ast.parse(open(path, encoding='utf-8').read())
        items = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                items.append((node.name, node.lineno, node.end_lineno))
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for n in ([target] if isinstance(target, ast.Name) else getattr(target, 'elts', [])):
                        if isinstance(n, ast.Name):
                            items.append((n.id, node.lineno, node.end_lineno))
        cache[path] = items
    return cache[path]


def ts_symbols(files):
    if not files:
        return {}
    helper = os.path.join('scripts', 'codemap_ts_index.cjs')
    res = subprocess.run(['node', helper, *files], capture_output=True, text=True, encoding='utf-8')
    if res.returncode != 0:
        sys.exit(f'Gagal menjalankan {helper}: {res.stderr.strip()}')
    return {k: [tuple(x) for x in v] for k, v in json.loads(res.stdout).items()}


def main():
    notes = load_notes()
    if not notes:
        sys.exit('docs/codemap kosong atau tidak ditemukan.')
    errs = []
    check_links(notes, errs)

    rows = table_rows(notes)
    ts_index = ts_symbols(sorted({r[1] for r in rows if r[1].endswith(('.ts', '.tsx')) and os.path.exists(r[1])}))
    py_cache = {}
    verified = labels = 0
    for name, path, symbol, start, end in rows:
        if not os.path.exists(path):
            errs.append(f'{name}: file tidak ada: {path}')
            continue
        total = sum(1 for _ in open(path, encoding='utf-8', errors='ignore'))
        if not 1 <= start <= end <= total:
            errs.append(f'{name}: {path} L{start}-{end} di luar file ({total} baris)')
            continue
        sm = SYMBOL_CELL.fullmatch(symbol)
        if not sm:
            labels += 1
            continue
        if path.endswith('.py'):
            candidates = python_symbols(path, py_cache)
        elif path.endswith(('.ts', '.tsx')):
            candidates = ts_index.get(path, [])
        else:
            labels += 1
            continue
        hits = [(a, b) for (n, a, b) in candidates if n == sm.group(1)]
        if (start, end) in hits:
            verified += 1
        else:
            actual = ', '.join(f'L{a}-{b}' for a, b in hits) or 'tidak ditemukan'
            errs.append(f'{name}: {path} `{sm.group(1)}` tertulis L{start}-{end}, di kode: {actual}')

    print(f'catatan={len(notes)} simbol_terverifikasi={verified} label_dicek_batas={labels}')
    if errs:
        print(f'{len(errs)} TEMUAN:')
        print('\n'.join(f'- {e}' for e in errs))
        sys.exit(1)
    print('SEMUA CEK LULUS')


if __name__ == '__main__':
    main()
