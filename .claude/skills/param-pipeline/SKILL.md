---
name: param-pipeline
description: 새 파라미터 1개를 서브에이전트 협업으로 끝까지 적립한다 — data-gen(샘플 생성) → schemaMaker(스키마 적립, 메인 세션) → tester(테스트 확인) → 검증(pytest 전체) → code-review(SPEC 대조) → 커밋. 새 세트를 추가하고 싶을 때 사용자가 직접 호출한다.
disable-model-invocation: true
---

# param-pipeline

새 파라미터 하나를 samples → schema.json → tests → 커밋까지 한 사이클로 밀어붙이는 절차다.
각 단계는 서로 다른 에이전트가 맡고, 격리 규칙(`.claude/rules/agent-isolation.md`)을
그대로 지킨다 — schemaMaker는 별도 서브에이전트가 아니라 parser와 함께 메인 세션에서
직접 진행한다.

## 절차

1. **작업 준비**: `node tools/backlog.mjs list`로 현재 상태를 확인하고, `samples/`의
   마지막 set 번호를 확인한다 (`ls samples | tail`).

2. **소스 생성 — data-gen 서브에이전트**: 다음 set 번호로 새 파라미터 1개를 추가하도록
   위임한다. dtype은 schema.json 기준으로 적게 쓰인 것을 우선하고, offset은 기존 세트와
   최소 64바이트 이상 떨어뜨리도록 지시한다. `tools/gen_samples.py`(또는 분리된
   `tools/sample_params.py`)의 PARAMS에 추가되고 `verify_set`이 통과하는지 보고받는다.

3. **스키마 적립 — 메인 세션(schemaMaker)**: 새 세트의 `*_change.yaml`을 읽고
   `src/differ.py`로 diff 구간을 구한 뒤, `src/schema_maker.py`의 추론 결과를 확인한다.
   `schema.json`에 새 항목을 추가하기 전에 — provisional/ambiguous 여부와 근거를
   요약해 사용자에게 적립 여부를 확인한다(LB-118 승인 게이트). 사용자가 이후
   확인 없이 진행하라고 명시적으로 지시했다면 그 지시를 따르되, 파괴적이거나
   되돌리기 어려운 작업까지 확대 해석하지 않는다.

4. **테스트 확인 — tester 서브에이전트**: 새 세트에 대한 PyTest가 필요한지 확인하도록
   위임한다. 기존 테스트가 `glob("set*_a.bin")` 등으로 세트를 자동 discover하는
   구조라면 새 파일 추가 없이 커버될 수 있다 — tester가 직접 판단해 보고하게 한다.

5. **검증 — 메인 세션**: `.venv/Scripts/python.exe -m pytest tests/ -q`로 전체 스위트를
   돌려 회귀가 없는지 확인한다. 새 세트만 걸러 보려면 `-k set<NN>`을 쓴다.

6. **코드리뷰 — code-review 서브에이전트**: 이번에 바뀐 것(schema.json의 새 항목,
   samples/의 새 세트, tools/의 PARAMS 변경)이 SPEC.md·격리 규칙과 어긋나지 않는지
   검토하도록 위임한다. 코드는 고치지 않는다.

7. **정리와 커밋 — 메인 세션**: code-review가 위생 문제(예: `backups/`의 stray
   `__pycache__`)를 지적하면 반영 여부를 판단해 정리한다. `backlog.json`은
   `tools/backlog.mjs`에 `add` 명령이 없으면 새 항목을 만들지 않는다 — 손으로
   고치지 않는다. 이번 사이클에서 실제로 바뀐 파일만 골라 커밋하고(사전에 이미
   있던 무관한 drift는 건드리지 않는다), 원격 저장소가 연결돼 있다면 push까지
   진행한다.

## 각 단계에서 지키는 것

- data-gen은 `schema.json`·`src/`·`tests/`를 읽지 않는다.
- tester는 `src/`·`schema.json`·`tools/gen_samples.py`(또는 `sample_params.py`)를
  읽지 않는다.
- code-review는 코드를 고치지 않고 보고만 한다.
- `samples/`의 기존 파일은 수정·삭제하지 않는다 — 새 세트만 추가한다.
