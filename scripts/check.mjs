// Checks every example folder: run `node scripts/check.mjs` (or `make check`) before a pull request.
//
// - an inquir.yaml, a Dockerfile and a README.md (with Russian and English sections);
// - a stack (a folder with an inquir-compose.yaml): its README.md, every imageRef pinned by digest in
//   registry form (docker.io/library/postgres@sha256:...), and each service subfolder checked as above
//   (an inquir.yaml and a Dockerfile; the stack's README.md covers it);
// - every FROM pinned by digest, the final stage not running as root, every COPY source inside the folder;
// - Python: requirements.txt pinned with hashes and installed with --require-hashes; the code compiles;
// - Node: exact versions in package.json, a package-lock.json with an integrity hash per package; node --check;
// - no secrets anywhere in the repository: nothing shaped like a Telegram token, an API key or a private key.
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const problems = [];
const fail = (where, message) => problems.push(`${where}: ${message}`);
const SECRET_PATTERNS = [/\b\d{8,10}:[A-Za-z0-9_-]{35}\b/, /\bsk-[A-Za-z0-9_-]{20,}/, /-----BEGIN [A-Z ]*PRIVATE KEY-----/, /\bgh[pousr]_[A-Za-z0-9]{36}\b/];

const examples = readdirSync(root).filter((name) => !name.startsWith('.') && name !== 'scripts'
  && statSync(join(root, name)).isDirectory());
if (!examples.length) fail('.', 'no example folders');

function run(command, args) {
  try {
    execFileSync(command, args, { stdio: 'pipe' });
    return null;
  } catch (error) {
    if (error.code === 'ENOENT') return 'skipped';
    return String(error.stderr || error.message).trim().split('\n').slice(-3).join(' ');
  }
}

function checkReadme(name, dir) {
  const readme = existsSync(join(dir, 'README.md')) ? readFileSync(join(dir, 'README.md'), 'utf8') : '';
  if (!readme) fail(name, 'missing README.md');
  else if (!readme.includes('## Русский') || !readme.includes('## English')) fail(name, 'README.md needs "## Русский" and "## English" sections');
}

for (const name of examples) {
  const dir = join(root, name);
  if (!existsSync(join(dir, 'inquir-compose.yaml'))) {
    checkReadme(name, dir);
    checkService(name, dir);
    continue;
  }
  // A stack: the README is the stack's; every folder next to inquir-compose.yaml is one service.
  checkReadme(name, dir);
  const compose = readFileSync(join(dir, 'inquir-compose.yaml'), 'utf8');
  for (const [, ref] of compose.matchAll(/^\s*imageRef:\s*(\S+)/gm)) {
    if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+(:\d+)?\/[a-z0-9._\/-]+@sha256:[a-f0-9]{64}$/.test(ref)) {
      fail(name, `imageRef must be pinned by digest in registry form (docker.io/library/postgres@sha256:...): ${ref}`);
    }
  }
  const services = readdirSync(dir, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => entry.name);
  for (const [, path] of compose.matchAll(/^\s*path:\s*\.\/(\S+?)\/?\s*(#.*)?$/gm)) {
    if (!services.includes(path)) fail(name, `path service ./${path} is not a folder here`);
  }
  for (const service of services) checkService(`${name}/${service}`, join(dir, service));
}

function checkService(name, dir) {
  const files = readdirSync(dir);
  for (const required of ['inquir.yaml', 'Dockerfile']) if (!files.includes(required)) fail(name, `missing ${required}`);
  const dockerfile = files.includes('Dockerfile') ? readFileSync(join(dir, 'Dockerfile'), 'utf8') : '';
  for (const line of dockerfile.split('\n').filter((entry) => entry.startsWith('FROM '))) {
    if (!/^FROM \S+@sha256:[a-f0-9]{64}( AS \S+)?$/.test(line)) fail(name, `FROM not pinned by digest: ${line}`);
  }
  // The final stage (after the last FROM) is what runs: its last USER must not be root, or,
  // without a USER line, its base must be an image that already runs as a regular user.
  const lines = dockerfile.split('\n');
  const finalStage = lines.slice(lines.findLastIndex((line) => line.startsWith('FROM ')));
  const user = finalStage.filter((line) => line.startsWith('USER ')).at(-1);
  const unprivilegedBase = /^FROM nginxinc\/nginx-unprivileged:/.test(finalStage[0] ?? '');
  if (user ? /^USER (root|0)(:|$)/.test(user) : !unprivilegedBase) fail(name, 'the Dockerfile must end on a non-root USER');
  for (const line of lines.filter((entry) => entry.startsWith('COPY ') && !/^COPY (--\S+ )*--from=/.test(entry))) {
    for (const source of line.replace(/^COPY /, '').split(/\s+/).slice(0, -1)) {
      if (source.startsWith('--')) continue;
      const found = source.includes('*')
        ? readdirSync(dir).some((entry) => new RegExp(`^${source.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*')}$`).test(entry))
        : existsSync(join(dir, source));
      if (!found) fail(name, `COPY source not in the folder: ${source}`);
    }
  }
  if (files.includes('requirements.txt')) {
    const requirements = readFileSync(join(dir, 'requirements.txt'), 'utf8');
    if (!dockerfile.includes('--require-hashes')) fail(name, 'pip install must use --require-hashes');
    for (const block of requirements.split(/\n(?=[A-Za-z])/).filter((entry) => /^[A-Za-z]/.test(entry))) {
      if (!/^[A-Za-z0-9._-]+==\S+ \\\n(\s+--hash=sha256:[a-f0-9]{64}( \\\n)?)+/.test(block)) fail(name, `requirement not pinned with a hash: ${block.split('\n')[0]}`);
    }
    for (const file of files.filter((entry) => entry.endsWith('.py'))) {
      const result = run('python3', ['-c', 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())', join(dir, file)]);
      if (result === 'skipped') { const again = run('python', ['-c', 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())', join(dir, file)]); if (again && again !== 'skipped') fail(name, `${file}: ${again}`); }
      else if (result) fail(name, `${file}: ${result}`);
    }
  }
  if (files.includes('package.json')) {
    const manifest = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'));
    for (const [dependency, version] of Object.entries(manifest.dependencies ?? {})) {
      if (!/^\d+\.\d+\.\d+$/.test(version)) fail(name, `${dependency} must be an exact version, got ${version}`);
    }
    if (!files.includes('package-lock.json')) fail(name, 'missing package-lock.json');
    else {
      const lock = JSON.parse(readFileSync(join(dir, 'package-lock.json'), 'utf8'));
      for (const [path, entry] of Object.entries(lock.packages ?? {})) {
        if (path && !/^sha512-/.test(entry.integrity ?? '')) fail(name, `${path} has no sha512 integrity in package-lock.json`);
      }
    }
    if (!dockerfile.includes('npm ci')) fail(name, 'install with npm ci (the lockfile)');
    for (const file of files.filter((entry) => /\.m?js$/.test(entry))) {
      const result = run(process.execPath, ['--check', join(dir, file)]);
      if (result && result !== 'skipped') fail(name, `${file}: ${result}`);
    }
  }
}

// Secrets: every file of the repository, at any depth (not .git, node_modules or certificates).
function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '.git' || entry.name === 'node_modules') continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.isFile() && !entry.name.endsWith('.pem')) yield path;
  }
}
for (const path of walk(root)) {
  if (path.endsWith(join('scripts', 'check.mjs'))) continue; // names the patterns
  const text = readFileSync(path, 'utf8');
  for (const pattern of SECRET_PATTERNS) {
    if (pattern.test(text)) fail(path.slice(root.length).replace(/^[\/]/, ''), `holds something shaped like a secret (${pattern})`);
  }
}

if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
console.log(`ok: ${examples.length} examples (${examples.join(', ')})`);
