import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();

function listDirs(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  return fs
    .readdirSync(dirPath, { withFileTypes: true })
    .filter((ent) => ent.isDirectory())
    .map((ent) => ent.name)
    .sort((a, b) => a.localeCompare(b));
}

function exists(p) {
  try {
    fs.accessSync(p, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

const appsDir = path.join(root, 'apps');
const toolsDir = path.join(root, 'tools');

const apps = listDirs(appsDir).map((name) => ({
  name,
  hasIndex: exists(path.join(appsDir, name, 'index.html')),
}));

const tools = listDirs(toolsDir).map((name) => ({
  name,
  hasReadme: exists(path.join(toolsDir, name, 'README.md')),
}));

const manifest = {
  generatedAt: new Date().toISOString(),
  apps,
  tools,
};

const outPath = path.join(appsDir, 'manifest.json');
fs.writeFileSync(outPath, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
console.log(`Wrote ${outPath}`);
