#!/usr/bin/env node
// lint: 저장소의 .mjs/.js 파일 구문을 node --check로 검사한다. 외부 패키지 없음.

import { spawnSync } from "node:child_process";
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const EXCLUDE_DIRS = new Set(["node_modules", ".git", ".venv", "samples"]);
const ROOT = process.cwd();

function collectFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (EXCLUDE_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      out.push(...collectFiles(full));
    } else if (/\.(mjs|js)$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

const files = collectFiles(ROOT);
let failed = false;

for (const file of files) {
  const result = spawnSync(process.execPath, ["--check", file], { encoding: "utf8" });
  if (result.status !== 0) {
    failed = true;
    console.error(`[lint] 구문 오류: ${file}`);
    console.error(result.stderr);
  }
}

if (failed) {
  process.exit(1);
}
console.log(`[lint] OK (${files.length}개 파일)`);
