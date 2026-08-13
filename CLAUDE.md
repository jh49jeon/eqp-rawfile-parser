# CLAUDE.md

## 명령어

- 이 저장소에는 package.json이 없다. npm 스크립트는 없다.
- `node tools/backlog.mjs list` — backlog.json의 작업을 id·상태·제목 순으로 한 줄씩 출력한다.
- `node tools/backlog.mjs set <id> <status>` — 지정한 작업의 status를 바꿔 backlog.json에 저장한다. enums.status에 없는 값은 거부한다.
- `node tools/backlog.mjs validate` — backlog.json의 필수 필드·enums 값·id 형식(LB-숫자3자리)을 검사해 VALID 또는 문제 목록을 출력한다.

## 구조

- `PLAN.md` — 이 과제의 실행 계약 원본. SPEC.md와 충돌하면 이 문서가 우선한다.
- `SPEC.md` — PLAN.md를 구현 명세로 내린 문서. backlog.json의 각 작업이 참조하는 근거 문서(`context_doc`)다.
- `backlog.json` — 작업 목록의 단일 진실 원천(SSOT)이다. `tools/backlog.mjs`로만 읽고 쓴다.
- `schema.json` — `parse()`에 주입되는 유일한 구조 정보. 최초에는 존재하지 않고 schemaMaker가 생성·적립한다.
- `src/parser.py` — `parse(path, schema) -> list[dict]` 호출 규약이 고정된 곳.
- `src/schema_maker.py` — A/B diff와 사용자 변경 진술로 파라미터 정의를 추론해 schema.json에 적립한다.
- `src/differ.py` — A/B 파일의 바이트 구간 차이를 계산한다.
- `samples/` — Phase 0에서 생성된 A/B 샘플 세트와 각 세트의 변경 진술(`*_change.yaml`)이 있다. hook으로 쓰기가 막혀 있다.
- `tests/` — Tester 서브에이전트만 작성하는 PyTest 파일이 있다.
- `.claude/settings.json` — PreToolUse hook(guard.py) 등록 설정이 있다.
- `.claude/agents/` — 서브에이전트 정의(data-gen, schema-maker, tester, code-review)가 있다.
- `.claude/hooks/guard.py` — samples/ 쓰기 차단과 `.tester-lock` 동안 src/·schema.json·tools/ 읽기 차단을 실행한다.
- `tools/gen_samples.py` — Phase 0 샘플 A/B 세트를 생성한다.
- `tools/backlog.mjs` — backlog.json을 list·set·validate하는 유일한 관리 스크립트.

## 항상 지킬 것

- backlog.json의 기록은 추가만 한다. 기존 항목의 근거나 이력을 지우지 않는다.
- 상태를 NG(blocked 등 실패·보류)로 남길 때는 반드시 조치 메모를 함께 남긴다.
- 외부 DB를 붙이지 않는다. 이 프로젝트의 상태는 로컬 파일(backlog.json, schema.json)로만 관리한다.
- backlog.json을 손으로 고치지 않는다. 읽기·쓰기 모두 `tools/backlog.mjs`로만 한다.

## 막히면

- `node tools/backlog.mjs validate`를 먼저 돌려 backlog.json 자체가 깨졌는지 확인한다.
- hook이 안 걸리는 것 같으면 `.claude/settings.json`의 hook command 경로가 실제 python.exe 절대경로인지 확인한다.
- 시스템 `python` 명령이 exit 49를 내면 Microsoft Store 스텁이다. `%LOCALAPPDATA%/Programs/Python/Python312/python.exe`를 직접 지정한다.
- `.tester-lock` 파일이 남아 있으면 src/·schema.json·tools/ 읽기가 전부 막힌다. Tester 실행이 끝났는데도 파일이 남아 있으면 지운다.
