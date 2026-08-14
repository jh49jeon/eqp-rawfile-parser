"""A/B diff + 변경 진술 → 파라미터 정의 추론. SPEC 5-1절, 4-1절, 4-2절.

pyyaml 의존을 피하려고 change.yaml(문법이 `key: value` 5줄로 고정됨)은 직접 파싱한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from codec import DTYPE_SIZES, decode, is_float_dtype
from differ import candidate_slices, diff_files

INT_TYPES = {"int16", "int32", "int64", "timestamp"}
FLOAT_TYPES = {"float32", "float64"}
CANDIDATE_DTYPES = ("int16", "int32", "int64", "float32", "float64", "timestamp")
ENDIANS = ("little", "big")
PRIORITY = {"int32": 1, "int64": 2, "int16": 3, "float32": 4, "float64": 5, "timestamp": 6}
ENDIAN_PRIORITY = {"little": 0, "big": 1}
EPOCH_RANGE = (1_000_000_000, 4_000_000_000)


def load_change(path: str | Path) -> dict:
    """samples/setNN_change.yaml을 읽는다. 형식은 SPEC 5절로 고정된 5개 키뿐이다."""
    result: dict = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"')
        result[key.strip()] = value
    return result


def _parse_display_value(text: str) -> tuple[int | float, bool]:
    is_float = "." in text
    return (float(text) if is_float else int(text)), is_float


def _value_matches(got: int | float, expected: int | float, is_float: bool) -> bool:
    if is_float:
        return math.isclose(got, expected, rel_tol=1e-4, abs_tol=1e-4)
    return got == expected


@dataclass(frozen=True)
class Candidate:
    offset: int
    size: int
    dtype: str
    endian: str


def find_matching_candidates(
    data_a: bytes, data_b: bytes, region: tuple[int, int], before: str, after: str
) -> list[Candidate]:
    """SPEC 5-1절 3~4단계. 후보 슬라이스를 전부 대입해 before/after 둘 다 맞는 것만 남긴다."""
    before_val, before_is_float = _parse_display_value(before)
    after_val, after_is_float = _parse_display_value(after)

    matches: list[Candidate] = []
    for offset, size in candidate_slices(region):
        for dtype in CANDIDATE_DTYPES:
            if size not in DTYPE_SIZES[dtype]:
                continue
            for endian in ENDIANS:
                try:
                    got_a = decode(data_a[offset:offset + size], dtype, endian, size)
                    got_b = decode(data_b[offset:offset + size], dtype, endian, size)
                except Exception:
                    continue
                if dtype == "timestamp" and not (
                    EPOCH_RANGE[0] <= got_a <= EPOCH_RANGE[1] and EPOCH_RANGE[0] <= got_b <= EPOCH_RANGE[1]
                ):
                    continue
                if _value_matches(got_a, before_val, before_is_float) and _value_matches(
                    got_b, after_val, after_is_float
                ):
                    matches.append(Candidate(offset, size, dtype, endian))
    return matches


@dataclass(frozen=True)
class InferOutcome:
    ok: bool
    reason: str | None = None
    chosen: Candidate | None = None
    ambiguous: bool = False
    rejected: list[Candidate] = field(default_factory=list)


def resolve_candidates(matches: list[Candidate], before_is_float: bool) -> InferOutcome:
    """SPEC 5-1절 5단계. 소수점 표기로 먼저 좁히고, 남으면 우선순위표로 하나를 고른다."""
    if not matches:
        return InferOutcome(False, "no_match")

    if before_is_float:
        narrowed = [m for m in matches if m.dtype in FLOAT_TYPES]
        if not narrowed:
            return InferOutcome(False, "notation_mismatch")
    else:
        narrowed = [m for m in matches if m.dtype in INT_TYPES]
        if not narrowed:
            narrowed = [m for m in matches if m.dtype in FLOAT_TYPES]
        if not narrowed:
            return InferOutcome(False, "no_match")

    narrowed = sorted(narrowed, key=lambda m: (PRIORITY[m.dtype], ENDIAN_PRIORITY[m.endian], m.offset))
    chosen, rejected = narrowed[0], narrowed[1:]
    return InferOutcome(True, chosen=chosen, ambiguous=bool(rejected), rejected=rejected)


def infer_parameter(path_a: str | Path, path_b: str | Path, change: dict) -> InferOutcome:
    """set 한 건의 A/B와 변경 진술로부터 파라미터 정의를 추론한다."""
    diff = diff_files(path_a, path_b)
    if not diff.ok:
        return InferOutcome(False, diff.reason)

    data_a = Path(path_a).read_bytes()
    data_b = Path(path_b).read_bytes()
    matches = find_matching_candidates(data_a, data_b, diff.region, change["before"], change["after"])
    _, before_is_float = _parse_display_value(change["before"])
    return resolve_candidates(matches, before_is_float)


def to_parameter_entry(change: dict, outcome: InferOutcome) -> dict:
    c = outcome.chosen
    return {
        "name": change["name"],
        "unit": change["unit"],
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
        "evidence": [{"set": change["set"], "before": change["before"], "after": change["after"]}],
        "superseded_by": None,
    }


def build_from_samples(samples_dir: Path) -> dict:
    """samples/ 아래 모든 setNN을 오름차순으로 순회하며 schema를 조립한다. LB-111.

    schema.json에 직접 쓰지 않는다 — SPEC 8절의 승인 지점이므로, 호출자가 결과를
    사람에게 보여주고 확인받은 뒤에만 파일로 저장해야 한다.
    """
    from schema_status import accumulate  # 지연 임포트: schema_status가 이 모듈을 되참조한다

    schema: dict = {"version": 0, "parameters": []}
    set_ids = sorted({p.stem[:-2] for p in samples_dir.glob("*_a.bin")})
    for set_id in set_ids:
        change = load_change(samples_dir / f"{set_id}_change.yaml")
        outcome = infer_parameter(
            samples_dir / f"{set_id}_a.bin", samples_dir / f"{set_id}_b.bin", change
        )
        if not outcome.ok:
            print(f"{set_id}: 실패 ({outcome.reason})")
            continue
        entry = to_parameter_entry(change, outcome)
        for line in accumulate(schema, entry):
            print(f"{set_id}: {line}")
    return schema


if __name__ == "__main__":
    _samples_dir = Path(__file__).resolve().parent.parent / "samples"
    _schema = build_from_samples(_samples_dir)
    print(f"\n총 {len(_schema['parameters'])}개 항목, version={_schema['version']}")
    print("이 출력은 미리보기입니다 — schema.json에 쓰려면 사람 승인 후 별도로 저장하세요.")
