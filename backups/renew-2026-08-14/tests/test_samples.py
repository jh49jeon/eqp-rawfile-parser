"""Phase 0 판정 테스트.

각 세트(set01~set15)의 _a.bin / _b.bin에 대해:
  - 두 파일의 바이트 길이가 같다
  - 두 파일 사이에 정확히 한 곳의 연속된(contiguous) 바이트 구간만 다르다

SPEC.md 7절 "Phase 0 — 샘플 생성" 판정 조건에 따른다.
이 테스트는 samples/*.bin만 읽으며 src/ · schema.json은 참조하지 않는다.
"""
import glob
import os

import pytest

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


def _discover_sets():
    a_files = sorted(glob.glob(os.path.join(SAMPLES_DIR, "set*_a.bin")))
    sets = []
    for a_path in a_files:
        base = os.path.basename(a_path)
        set_name = base[: -len("_a.bin")]
        sets.append(set_name)
    return sets


SET_NAMES = _discover_sets()


def _diff_regions(a_bytes: bytes, b_bytes: bytes):
    """a_bytes와 b_bytes 사이에서 서로 다른 바이트들의 연속 구간 목록을 반환한다.

    각 구간은 (start, end) 반개구간(half-open interval)이다.
    """
    diff_indexes = [i for i in range(len(a_bytes)) if a_bytes[i] != b_bytes[i]]
    if not diff_indexes:
        return []

    regions = []
    start = diff_indexes[0]
    prev = diff_indexes[0]
    for idx in diff_indexes[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        regions.append((start, prev + 1))
        start = idx
        prev = idx
    regions.append((start, prev + 1))
    return regions


@pytest.fixture(params=SET_NAMES)
def set_name(request):
    return request.param


def test_at_least_one_sample_set_discovered():
    assert len(SET_NAMES) > 0, "samples/ 아래에서 setNN_a.bin 파일을 찾지 못했다"


def test_ab_pair_same_length(set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    b_path = os.path.join(SAMPLES_DIR, f"{set_name}_b.bin")

    with open(a_path, "rb") as f:
        a_bytes = f.read()
    with open(b_path, "rb") as f:
        b_bytes = f.read()

    assert len(a_bytes) == len(b_bytes), (
        f"{set_name}: A/B 파일 길이가 다르다 (구조 불변 전제 위반) "
        f"a={len(a_bytes)} b={len(b_bytes)}"
    )


def test_ab_pair_single_contiguous_diff_region(set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    b_path = os.path.join(SAMPLES_DIR, f"{set_name}_b.bin")

    with open(a_path, "rb") as f:
        a_bytes = f.read()
    with open(b_path, "rb") as f:
        b_bytes = f.read()

    assert len(a_bytes) == len(b_bytes), f"{set_name}: 길이가 달라 diff 구간 판정이 무의미하다"

    regions = _diff_regions(a_bytes, b_bytes)

    assert len(regions) == 1, (
        f"{set_name}: 달라진 바이트 구간이 정확히 한 곳이어야 하는데 {len(regions)}곳이다: {regions}"
    )
