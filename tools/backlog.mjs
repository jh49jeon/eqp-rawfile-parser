#!/usr/bin/env node
// backlog.json 관리 스크립트. 외부 패키지 없이 Node 표준 기능만 사용한다.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const BACKLOG_PATH = join(HERE, "..", "backlog.json");

const REQUIRED_FIELDS = [
  "id",
  "status",
  "priority",
  "category",
  "title",
  "summary",
  "where",
  "parent",
  "deps",
  "doc",
  "done_at",
  "note",
];

const ID_PATTERN = /^LB-\d{3}$/;

function loadBacklog() {
  const raw = readFileSync(BACKLOG_PATH, "utf8");
  return JSON.parse(raw);
}

function saveBacklog(data) {
  writeFileSync(BACKLOG_PATH, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function cmdList() {
  const data = loadBacklog();
  for (const task of data.tasks) {
    console.log(`${task.id}\t${task.status}\t${task.title}`);
  }
}

function cmdSet(id, status) {
  if (!id || !status) {
    console.error("사용법: node tools/backlog.mjs set <id> <status>");
    process.exitCode = 1;
    return;
  }
  const data = loadBacklog();
  const validStatuses = data.enums?.status ?? [];
  if (!validStatuses.includes(status)) {
    console.error(
      `거부: '${status}'는 enums.status에 없는 값입니다. 허용된 값: ${validStatuses.join(", ")}`
    );
    process.exitCode = 1;
    return;
  }
  const task = data.tasks.find((t) => t.id === id);
  if (!task) {
    console.error(`거부: id '${id}'인 작업을 찾을 수 없습니다.`);
    process.exitCode = 1;
    return;
  }
  task.status = status;
  saveBacklog(data);
  console.log(`${task.id} 상태를 '${status}'로 변경했습니다.`);
}

function cmdValidate() {
  const data = loadBacklog();
  const problems = [];

  const statusEnum = data.enums?.status ?? [];
  const priorityEnum = data.enums?.priority ?? [];
  const categoryEnum = data.enums?.category ?? [];

  const seenIds = new Set();

  for (const [index, task] of data.tasks.entries()) {
    const label = task?.id ?? `#${index}`;

    for (const field of REQUIRED_FIELDS) {
      if (!(field in task)) {
        problems.push(`${label}: 필수 필드 '${field}'가 없습니다.`);
      }
    }

    if (typeof task.id === "string") {
      if (!ID_PATTERN.test(task.id)) {
        problems.push(`${label}: id 형식이 LB-숫자3자리가 아닙니다 ('${task.id}').`);
      }
      if (seenIds.has(task.id)) {
        problems.push(`${label}: id가 중복됩니다.`);
      }
      seenIds.add(task.id);
    }

    if (task.status !== undefined && !statusEnum.includes(task.status)) {
      problems.push(`${label}: status 값 '${task.status}'가 enums.status에 없습니다.`);
    }
    if (task.priority !== undefined && !priorityEnum.includes(task.priority)) {
      problems.push(`${label}: priority 값 '${task.priority}'가 enums.priority에 없습니다.`);
    }
    if (task.category !== undefined && !categoryEnum.includes(task.category)) {
      problems.push(`${label}: category 값 '${task.category}'가 enums.category에 없습니다.`);
    }
  }

  if (problems.length === 0) {
    console.log("VALID");
  } else {
    console.log(`INVALID (${problems.length}건)`);
    for (const problem of problems) {
      console.log(`- ${problem}`);
    }
    process.exitCode = 1;
  }
}

function main() {
  const [, , command, ...rest] = process.argv;

  switch (command) {
    case "list":
      cmdList();
      break;
    case "set":
      cmdSet(rest[0], rest[1]);
      break;
    case "validate":
      cmdValidate();
      break;
    default:
      console.error("사용법: node tools/backlog.mjs <list|set|validate> ...");
      process.exitCode = 1;
  }
}

main();
