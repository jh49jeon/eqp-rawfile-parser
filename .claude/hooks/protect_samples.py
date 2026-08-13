#!/usr/bin/env python3
"""samples/ 아래 파일에 대한 에이전트의 직접 수정을 차단한다.

SPEC 8절. 업로드 원본이 수정되면 "A와 B는 값 하나만 다르다"는 Phase 0 전제가
무너지고, 그 위에 선 diff 추론 전체가 근거를 잃는다.

샘플 생성 자체는 Bash로 실행하는 tools/gen_samples.py가 담당하므로
이 훅(Write/Edit 계열 차단)에 걸리지 않는다.
"""

import json
import sys
from pathlib import Path

PROTECTED = "samples"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # 훅이 입력을 못 읽었다고 해서 작업을 막지는 않는다.
        return 0

    raw_path = payload.get("tool_input", {}).get("file_path")
    if not raw_path:
        return 0

    try:
        target = Path(raw_path).resolve()
        guarded = (Path.cwd() / PROTECTED).resolve()
    except OSError:
        return 0

    if guarded == target or guarded in target.parents:
        print(
            f"차단: {PROTECTED}/ 아래 파일은 수정할 수 없습니다 ({target.name}).\n"
            "업로드 원본이 바뀌면 A/B 전제가 무너져 schemaMaker의 추론 근거가 사라집니다.\n"
            "샘플을 다시 만들어야 한다면 tools/gen_samples.py를 쓰세요.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
