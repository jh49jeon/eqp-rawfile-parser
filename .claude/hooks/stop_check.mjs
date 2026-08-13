#!/usr/bin/env node
// Stop hook: 응답을 끝내기 전에 lint·build·typecheck·파일 길이(300줄)를 검사한다.
// 넷 중 하나라도 실패하면 종료를 막고 실패 내용을 stderr로 돌려준다.
// stop_hook_active가 true면 이미 한 번 이 훅 때문에 재시도한 상태이므로
// 같은 실패가 무한 반복되는 것을 막기 위해 그냥 통과시킨다.

import { spawnSync } from "node:child_process";
import { readdirSync, statSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const MAX_LINES = 300;
const LINE_CHECK_DIRS = ["src", "tools", "tests"];
const LINE_CHECK_EXT = /\.(py|mjs|js)$/;
const EXCLUDE_DIRS = new Set(["node_modules", ".git", ".venv", "samples"]);

function readStdin() {
  try {
    const raw = readFileSync(0, "utf8");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function runScript(name) {
  const result = spawnSync("npm", ["run", "--silent", name], {
    encoding: "utf8",
    shell: true,
  });
  return {
    name,
    ok: result.status === 0,
    output: `${result.stdout ?? ""}${result.stderr ?? ""}`.trim(),
  };
}

function collectFiles(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (EXCLUDE_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      out.push(...collectFiles(full));
    } else if (LINE_CHECK_EXT.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

function checkFileLength() {
  const offenders = [];
  for (const dir of LINE_CHECK_DIRS) {
    for (const file of collectFiles(join(process.cwd(), dir))) {
      const lineCount = readFileSync(file, "utf8").split("\n").length;
      if (lineCount > MAX_LINES) {
        offenders.push(`${file} (${lineCount}줄)`);
      }
    }
  }
  return {
    name: "file-length",
    ok: offenders.length === 0,
    output: offenders.length
      ? `300줄을 넘는 파일:\n${offenders.map((o) => `  - ${o}`).join("\n")}`
      : "",
  };
}

function main() {
  const payload = readStdin();

  if (payload.stop_hook_active === true) {
    process.exit(0);
  }

  const results = [
    runScript("lint"),
    runScript("build"),
    runScript("typecheck"),
    checkFileLength(),
  ];

  const failures = results.filter((r) => !r.ok);

  if (failures.length === 0) {
    process.exit(0);
  }

  for (const f of failures) {
    console.error(`[stop-check] 실패: ${f.name}`);
    if (f.output) console.error(f.output);
  }
  process.exit(2);
}

main();
