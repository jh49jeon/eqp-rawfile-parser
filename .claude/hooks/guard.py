#!/usr/bin/env python3
"""에이전트 경계를 강제하는 PreToolUse 훅. SPEC 6절·8절.

세 가지를 막는다.

1. samples/ 아래 파일의 수정 (Write·Edit 계열)
   업로드 원본이 바뀌면 "A와 B는 값 하나만 다르다"는 전제가 무너져
   diff 추론 전체가 근거를 잃는다.

2. Tester가 도는 동안 src/ 와 schema.json 읽기 (Read 계열)
   Tester가 파서를 보고 기대값을 쓰면 PyTest 통과가 자기채점이 된다.
   기대값은 오직 변경 진술에서만 나와야 한다.

3. backlog.json을 파일 도구로 직접 읽거나 쓰는 것 (Read·Write 계열 모두)
   backlog.json은 tools/backlog.mjs가 유일한 관리 창구다. 직접 손대면
   enums 검증·id 형식 검사를 거치지 않은 채 SSOT가 깨질 수 있다.

2번의 판정 방식: Tester를 띄우기 전에 메인 에이전트가 잠금 파일을 만들고,
끝나면 지운다. 훅 payload에 서브에이전트 식별자가 실려 오는지 확실하지 않아
호출자 신원에 의존하지 않는 방식을 택했다. 잠금이 걸린 동안에는 누구든
막히므로 우회 경로가 없다.

payload에 신원 정보가 실려 오면 DIAG_LOG에 쌓이므로 나중에 확인할 수 있다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
READ_TOOLS = {"Read", "Glob", "Grep", "NotebookRead"}

PROTECTED_WRITE = ("samples",)
PROTECTED_READ = ("src", "schema.json", "tools")
BACKLOG_FILE = "backlog.json"
BACKLOG_TOOLS = WRITE_TOOLS | READ_TOOLS

HOOK_DIR = Path(__file__).resolve().parent
LOCK = HOOK_DIR / ".tester-lock"
DIAG_LOG = HOOK_DIR / "payload-shape.log"

BLOCK = 2
ALLOW = 0


def resolve(path_str: str) -> Path | None:
    try:
        return Path(path_str).resolve()
    except (OSError, ValueError):
        return None


def is_under(target: Path, name: str) -> bool:
    """target이 프로젝트 루트의 name 아래(또는 그 자신)인가."""
    root = Path.cwd().resolve()
    try:
        guarded = (root / name).resolve()
    except OSError:
        return False
    return target == guarded or guarded in target.parents


def record_payload_shape(payload: dict) -> None:
    """payload의 최상위 키만 남긴다. 나중에 신원 필드 유무를 판단하기 위한 것."""
    try:
        shape = sorted(payload.keys())
        if DIAG_LOG.exists() and DIAG_LOG.read_text(encoding="utf-8").strip() == str(shape):
            return
        DIAG_LOG.write_text(str(shape), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    try:
        # Windows 쪽 호출부가 stdin에 UTF-8 BOM을 붙여 보내는 경우가 있다.
        # BOM이 있으면 json.load(sys.stdin)이 JSONDecodeError를 내고 그걸
        # 삼켜 ALLOW로 빠지면서 훅이 통째로 무력화된다 — utf-8-sig로 읽어 방지한다.
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        # 훅이 입력을 못 읽었다고 해서 작업을 막지는 않는다.
        return ALLOW

    record_payload_shape(payload)

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    raw = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path")
    if not raw:
        return ALLOW

    target = resolve(str(raw))
    if target is None:
        return ALLOW

    if tool in BACKLOG_TOOLS and target.name == BACKLOG_FILE and is_under(target, "."):
        print(
            "차단: 백로그는 tools/backlog.mjs로만 읽고 수정할 수 있습니다. list/set/validate를 쓰세요.",
            file=sys.stderr,
        )
        return BLOCK

    if tool in WRITE_TOOLS:
        for name in PROTECTED_WRITE:
            if is_under(target, name):
                print(
                    f"차단: {name}/ 아래 파일은 수정할 수 없습니다 ({target.name}).\n"
                    "업로드 원본이 바뀌면 A/B 전제가 무너져 추론 근거가 사라집니다.\n"
                    "샘플을 다시 만들어야 한다면 tools/gen_samples.py를 쓰세요.",
                    file=sys.stderr,
                )
                return BLOCK

    if tool in READ_TOOLS and LOCK.exists():
        for name in PROTECTED_READ:
            if is_under(target, name):
                print(
                    f"차단: Tester가 실행 중인 동안 {name} 은(는) 읽을 수 없습니다.\n"
                    "테스트의 기대값은 파서가 아니라 samples/의 변경 진술에서만 나와야 합니다.\n"
                    "필요한 호출 규약은 SPEC.md 3절에 있습니다.",
                    file=sys.stderr,
                )
                return BLOCK

    return ALLOW


if __name__ == "__main__":
    sys.exit(main())
