// Helper untuk scripts/check_codemap.py: daftar deklarasi (fungsi, variabel, interface)
// di file TS/TSX beserta baris awal-akhir, dalam format JSON.
const ts = require(require('path').join(process.cwd(), 'node_modules', 'typescript'));
const fs = require('fs');

const out = {};
for (const f of process.argv.slice(2)) {
  const src = ts.createSourceFile(f, fs.readFileSync(f, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const ln = (p) => src.getLineAndCharacterOfPosition(p).line + 1;
  const items = [];
  const visit = (node, depth) => {
    if ((ts.isFunctionDeclaration(node) || ts.isInterfaceDeclaration(node)) && node.name) {
      items.push([node.name.text, ln(node.getStart()), ln(node.end)]);
    }
    if (ts.isVariableStatement(node)) {
      for (const d of node.declarationList.declarations) {
        if (ts.isIdentifier(d.name)) items.push([d.name.text, ln(node.getStart()), ln(node.end)]);
      }
    }
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) {
      items.push([node.name.text, ln(node.getStart()), ln(node.end)]);
    }
    if (depth < 14) ts.forEachChild(node, (c) => visit(c, depth + 1));
  };
  visit(src, 0);
  out[f] = items;
}
console.log(JSON.stringify(out));
