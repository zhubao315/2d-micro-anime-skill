#!/usr/bin/env node
/* eslint-disable no-console */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const PKG = require('../package.json');
const SOURCE = path.resolve(__dirname, '..');
const MARKER = '.2d-micro-anime-skill-installed';
const SKILL_NAME = '2d-micro-anime';
const TARGETS = {
  opencode: [process.env.OPENCODE_CONFIG_DIR && path.join(process.env.OPENCODE_CONFIG_DIR, 'skills'),
    path.join(os.homedir(), '.config', 'opencode', 'skills'),
    path.join(os.homedir(), '.opencode', 'skills')],
  claude: [path.join(os.homedir(), '.claude', 'skills')],
  agents: [path.join(os.homedir(), '.agents', 'skills')],
  codex: [path.join(os.homedir(), '.codex', 'skills')],
  cursor: [path.join(os.homedir(), '.cursor', 'skills')],
  project: [path.join(process.cwd(), '.opencode', 'skills')],
  'project-claude': [path.join(process.cwd(), '.claude', 'skills')],
};

function help() {
  console.log(`${PKG.name} v${PKG.version}
一键把「2D 微动漫全流程 Skill」安装到 Agent 的 skills 目录。

用法:
  npx ${PKG.name} install [目标目录] [选项]
  npx ${PKG.name} check
  npx ${PKG.name} uninstall [目标目录] [选项]

选项:
  -t, --target <名称>   opencode | claude | agents | codex | cursor | project | project-claude
                       （默认自动探测已存在的 skills 目录）
  -l, --link           用符号链接而非复制（改仓库源码后即时生效）
  -f, --force          目标已存在时强制覆盖
  -h, --help           显示帮助

示例:
  npx ${PKG.name} install                       # 自动探测并安装
  npx ${PKG.name} install --target opencode     # 装到 OpenCode
  npx ${PKG.name} install --target claude       # 装到 Claude Code
  npx ${PKG.name} install ./my-project/skills   # 装到自定义目录
  npm install -g ${PKG.name} && anime-skill install
`);
}

function parse(argv) {
  const out = { cmd: argv[0] || 'help', target: null, link: false, force: false, dir: null, source: false };
  if (['-h', '--help', 'help'].includes(out.cmd)) out.cmd = 'help';
  for (let i = 1; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-t' || a === '--target') out.target = argv[++i];
    else if (a === '-l' || a === '--link') out.link = true;
    else if (a === '-f' || a === '--force') out.force = true;
    else if (a === '-h' || a === '--help') out.cmd = 'help';
    else if (a === '--source') out.source = true;
    else if (!a.startsWith('-')) out.dir = a;
  }
  return out;
}

function allCandidates(target) {
  if (target) {
    if (!TARGETS[target]) throw new Error(`未知 target: ${target}（可选: ${Object.keys(TARGETS).join(', ')}）`);
    return TARGETS[target].filter(Boolean);
  }
  return Object.values(TARGETS).flat().filter(Boolean);
}

function resolveBase(opts) {
  if (opts.dir) return path.resolve(opts.dir);
  const candidates = allCandidates(opts.target);
  const existing = candidates.find((p) => fs.existsSync(p) && fs.statSync(p).isDirectory());
  return existing || candidates.find(Boolean);
}

function validateSource() {
  for (const f of ['SKILL.md', 'README.md', 'references', 'templates', 'engine']) {
    if (!fs.existsSync(path.join(SOURCE, f))) throw new Error(`源目录缺少 ${f}，可能不是完整的 skill 仓库: ${SOURCE}`);
  }
}

function verifyDir(skillDir) {
  const need = ['SKILL.md', 'references/01-planning.md', 'references/03-animation.md',
    'references/07-ai-video-h3.md', 'templates/scene-template.py', 'engine/warp.py', 'engine/render.py'];
  const missing = need.filter((f) => !fs.existsSync(path.join(skillDir, f)));
  return { skillDir, ok: missing.length === 0, missing };
}

function verify(dest) {
  return verifyDir(path.join(dest, SKILL_NAME));
}

function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    if (e.name === '.git' || e.name === 'node_modules') continue;
    const s = path.join(src, e.name);
    const d = path.join(dst, e.name);
    if (e.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function install(opts) {
  validateSource();
  const base = resolveBase(opts);
  const dest = path.join(base, SKILL_NAME);
  if (fs.existsSync(dest)) {
    if (!opts.force) {
      console.error(`目标已存在: ${dest}\n如需覆盖请加 --force`);
      process.exitCode = 1;
      return;
    }
    fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.mkdirSync(base, { recursive: true });
  if (opts.link) {
    fs.symlinkSync(SOURCE, dest, 'dir');
    console.log(`已链接: ${dest} -> ${SOURCE}`);
  } else {
    copyDir(SOURCE, dest);
    console.log(`已安装: ${dest}`);
  }
  fs.writeFileSync(path.join(dest, MARKER), JSON.stringify({
    name: PKG.name, version: PKG.version, source: SOURCE, installedAt: new Date().toISOString(),
  }, null, 2));
  check({ ...opts, dir: base });
}

function check(opts) {
  const r = opts.source ? verifyDir(SOURCE)
    : verify(opts.dir ? path.resolve(opts.dir) : resolveBase(opts));
  if (r.ok) {
    console.log(`✓ 安装校验通过: ${r.skillDir}`);
  } else {
    console.error(`✗ 安装不完整: ${r.skillDir}\n  缺少: ${r.missing.join(', ')}`);
    process.exitCode = 1;
  }
}

function uninstall(opts) {
  const base = resolveBase(opts);
  const dest = path.join(base, SKILL_NAME);
  if (!fs.existsSync(dest)) {
    console.log(`未安装: ${dest}`);
    return;
  }
  if (!fs.existsSync(path.join(dest, MARKER))) {
    console.error(`拒绝删除：目标不是本工具安装的（缺少 ${MARKER}）: ${dest}`);
    process.exitCode = 1;
    return;
  }
  fs.rmSync(dest, { recursive: true, force: true });
  console.log(`已卸载: ${dest}`);
}

function main() {
  const opts = parse(process.argv.slice(2));
  if (opts.cmd === 'help' || process.argv.length <= 2) return help();
  try {
    if (opts.cmd === 'install') install(opts);
    else if (opts.cmd === 'check') check(opts);
    else if (opts.cmd === 'uninstall') uninstall(opts);
    else {
      console.error(`未知命令: ${opts.cmd}`);
      help();
      process.exitCode = 1;
    }
  } catch (e) {
    console.error(`错误: ${e.message}`);
    process.exitCode = 1;
  }
}

main();
