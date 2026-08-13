#!/usr/bin/env node
// typecheck: src/의 .py 파일을 py_compile로 컴파일해본다.
// 이 저장소는 mypy 등 외부 타입 체커를 쓰지 않으므로, "타입 체크"의 실질은
// 파이썬 소스가 최소한 파싱·컴파일되는지 확인하는 것으로 대체한다.

import { spawnSync } from "node:child_process";
import { readdirSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";

const EXCLUDE_DIRS = new Set(["node_modules", ".git", ".venv", "samples"]);
const ROOT = process.cwd();

const PYTHON_CANDIDATES = [
  "C:/Users/opera star seo/AppData/Local/Programs/Python/Python312/python.exe",
  "py",
  "python3",
  "python",
];

function findPython() {
  for (const candidate of PYTHON_CANDIDATES) {
    const result = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (result.status === 0) return candidate;
  }
  return null;
}

function collectPyFiles(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (EXCLUDE_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      out.push(...collectPyFiles(full));
    } else if (entry.endsWith(".py")) {
      out.push(full);
    }
  }
  return out;
}

const files = [
  ...collectPyFiles(join(ROOT, "src")),
  ...collectPyFiles(join(ROOT, "tests")),
];

if (files.length === 0) {
  console.log("[typecheck] 대상 .py 파일 없음 — 통과 처리");
  process.exit(0);
}

const python = findPython();
if (!python) {
  console.error("[typecheck] 실행 가능한 python을 찾지 못했습니다.");
  process.exit(1);
}

let failed = false;
for (const file of files) {
  const result = spawnSync(python, ["-m", "py_compile", file], { encoding: "utf8" });
  if (result.status !== 0) {
    failed = true;
    console.error(`[typecheck] 컴파일 실패: ${file}`);
    console.error(result.stderr);
  }
}

if (failed) {
  process.exit(1);
}
console.log(`[typecheck] OK (${files.length}개 파일, ${python})`);
