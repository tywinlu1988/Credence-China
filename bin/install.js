#!/usr/bin/env node
/* Credence 安装引导器（npx bootstrapper）。
 *
 * 把仓库内当前 release 包（version/<v>-release/，单一可安装包）复制为一个可直接
 * 用 agent CLI 打开的项目目录。用法：
 *
 *   npx github:tywinlu1988/fixedincome [目标目录名]      （默认目录名 credence）
 *
 * 设计说明：本仓库经 GitHub 清理后，version/ 下仅保留当前一个 *-release 发行包
 * （历史快照在 git 标签、分发 zip 在 GitHub Releases）。npx 从 git 树下载的正是
 * 被跟踪的内容，因此 version/ 下只会找到这一个 release 目录——item1 的清理让
 * 本引导器无需硬编码版本号即可稳健定位。
 */
const fs = require('fs');
const path = require('path');

const pkgRoot = path.join(__dirname, '..');
const versionDir = path.join(pkgRoot, 'version');

function findReleaseDir(dir) {
  if (!fs.existsSync(dir)) return null;
  const releases = fs.readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && /-release$/.test(e.name))
    .map((e) => e.name)
    .sort();
  return releases.length ? path.join(dir, releases[releases.length - 1]) : null;
}

function main() {
  const src = findReleaseDir(versionDir);
  if (!src) {
    console.error('✗ 未在仓库中找到 release 包（version/*-release/）。');
    console.error('  请改从 GitHub Releases 下载 zip：');
    console.error('  https://github.com/tywinlu1988/fixedincome/releases');
    process.exit(1);
  }

  const destName = process.argv[2] || 'credence';
  const dest = path.join(process.cwd(), destName);
  if (fs.existsSync(dest)) {
    console.error(`✗ 目标目录已存在：${dest}`);
    console.error('  请换一个目录名，或先删除该目录。');
    process.exit(1);
  }

  fs.cpSync(src, dest, { recursive: true });

  const rel = path.basename(src);
  console.log(`✓ Credence（${rel}）已安装到 ${dest}`);
  console.log('');
  console.log('下一步：用你的 agent CLI 打开该目录（把包根当项目），随口提问即可，');
  console.log('例如“帮我看看这家公司”“这个组合有没有问题”。详见包内 INSTALL.md / AGENTS.md。');
}

main();
