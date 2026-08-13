"""schema.json 항목의 상태 전이. SPEC 4-1절(status), 4-2절(오프셋 겹침 처리).

schema_maker.py에서 분리했다 — 추론(5-1절)과 적립 후 상태 관리(4-1·4-2절)는
서로 다른 관심사이고, 한 파일에 합치면 300줄 제한을 넘는다.
"""

from __future__ import annotations

from pathlib import Path

from differ import diff_files
from schema_maker import (
    Candidate,
    InferOutcome,
    _parse_display_value,
    find_matching_candidates,
    resolve_candidates,
)

USED_STATUSES = ("confirmed", "provisional")
OVERLAP_CHAIN_LIMIT = 3


def _overlaps(a: dict, b: dict) -> bool:
    a_lo, a_hi = a["offset"], a["offset"] + a["size"]
    b_lo, b_hi = b["offset"], b["offset"] + b["size"]
    return a_lo < b_hi and b_lo < a_hi


def accumulate(schema: dict, entry: dict) -> list[str]:
    """4절 불변 조건을 지키며 schema에 항목을 적립한다. 4-2절 겹침 처리 포함.

    겹침이 OVERLAP_CHAIN_LIMIT개 이상 연쇄하면 자동 강등을 멈추고 사람에게 보고한다
    (SPEC 4-2절) — schema는 건드리지 않고 새 항목도 적립하지 않는다.

    반환값은 이번 호출에서 벌어진 일을 사람이 읽을 로그 줄로 남긴 것이다.
    """
    log: list[str] = []
    params = schema.setdefault("parameters", [])

    existing_same_name = [p for p in params if p["name"] == entry["name"] and p["status"] != "deprecated"]
    if existing_same_name:
        log.append(f"거부: '{entry['name']}'이 이미 있습니다 (name 유일성 위반) — 4-1절 정정 흐름으로 처리하세요.")
        return log

    overlapping = [
        existing
        for existing in params
        if existing["status"] in USED_STATUSES and _overlaps(existing, entry)
    ]

    if len(overlapping) >= OVERLAP_CHAIN_LIMIT:
        names = ", ".join(e["name"] for e in overlapping)
        log.append(
            f"중단: '{entry['name']}'이 기존 항목 {len(overlapping)}개({names})와 동시에 겹쳤습니다 "
            f"— 연쇄 강등({OVERLAP_CHAIN_LIMIT}개 이상)은 자동 처리하지 않고 사람에게 보고합니다. "
            "schema는 변경되지 않았습니다."
        )
        return log

    for existing in overlapping:
        existing["status"] = "disputed"
        existing["disputed_reason"] = "offset_overlap"
        existing["disputed_by"] = entry["name"]
        existing["disputed_at_set"] = entry["evidence"][0]["set"]
        log.append(f"강등: '{existing['name']}' → disputed (겹침, 새 항목 '{entry['name']}'이 더 강한 근거)")

    params.append(entry)
    schema["version"] = schema.get("version", 0) + 1
    tag = "provisional" if entry["ambiguous"] else "confirmed"
    log.append(f"적립: '{entry['name']}' @ 0x{entry['offset']:04X} ({entry['dtype']}/{entry['endian']}, {tag})")
    return log


def _build_reinferred_entry(disputed_entry: dict, outcome: InferOutcome) -> dict:
    c = outcome.chosen
    return {
        "name": disputed_entry["name"],
        "unit": disputed_entry["unit"],
        "offset": c.offset,
        "size": c.size,
        "dtype": c.dtype,
        "endian": c.endian,
        "table": None,
        "row": None,
        "column": None,
        "status": "provisional" if outcome.ambiguous else "confirmed",
        "ambiguous": outcome.ambiguous,
        "rejected_candidates": [
            {"offset": r.offset, "size": r.size, "dtype": r.dtype, "endian": r.endian}
            for r in outcome.rejected
        ],
        "evidence": list(disputed_entry["evidence"]),
        "superseded_by": None,
    }


def reinfer_disputed(schema: dict, samples_dir: Path, disputed_entry: dict) -> list[str]:
    """4-2절 재추론 경로. `disputed_entry`의 evidence 전체로 5-1절 탐색을 다시 돌리되,
    다른 사용 중(confirmed/provisional) 항목이 점유한 구간을 침범하는 후보는 제외한다.

    성공하면 새 항목을 적립하고 disputed_entry는 `deprecated` + `superseded_by`로 넘긴다.
    disputed_entry는 schema['parameters'] 안의 객체 그대로 넘겨야 제자리에서 갱신된다.
    """
    log: list[str] = []
    evidence = disputed_entry.get("evidence", [])
    if not evidence:
        log.append(f"재추론 실패: '{disputed_entry['name']}'에 evidence가 없습니다.")
        return log

    occupied = [
        p
        for p in schema.get("parameters", [])
        if p is not disputed_entry and p["status"] in USED_STATUSES
    ]

    candidate_sets: list[set[Candidate]] = []
    before_is_float = False
    for ev in evidence:
        path_a = Path(samples_dir) / f"{ev['set']}_a.bin"
        path_b = Path(samples_dir) / f"{ev['set']}_b.bin"
        diff = diff_files(path_a, path_b)
        if not diff.ok:
            log.append(f"재추론 실패: {ev['set']} diff 실패 ({diff.reason})")
            return log
        data_a = path_a.read_bytes()
        data_b = path_b.read_bytes()
        matches = find_matching_candidates(data_a, data_b, diff.region, ev["before"], ev["after"])
        candidate_sets.append(set(matches))
        _, before_is_float = _parse_display_value(ev["before"])

    intersected = set.intersection(*candidate_sets) if candidate_sets else set()
    filtered = [
        c
        for c in intersected
        if not any(_overlaps({"offset": c.offset, "size": c.size}, o) for o in occupied)
    ]

    outcome = resolve_candidates(filtered, before_is_float)
    if not outcome.ok:
        log.append(f"재추론 실패: '{disputed_entry['name']}' ({outcome.reason})")
        return log

    new_entry = _build_reinferred_entry(disputed_entry, outcome)
    prior_status = disputed_entry["status"]
    disputed_entry["status"] = "deprecated"  # name 유일성 검사를 통과시키려면 적립 전에 내려야 한다
    accum_log = accumulate(schema, new_entry)
    log.extend(accum_log)
    if any(line.startswith("적립:") for line in accum_log):
        disputed_entry["superseded_by"] = new_entry["name"]
        log.append(f"이력: '{disputed_entry['name']}' (disputed) → deprecated, superseded_by={new_entry['name']}")
    else:
        disputed_entry["status"] = prior_status  # 적립 실패(연쇄 겹침 등) 시 되돌린다

    return log
