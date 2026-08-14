"""A/B 파일 바이트 구간 diff. SPEC.md 5-1절 1~2단계.

SPEC 1절 전제: 테이블 구조가 불변이므로 A/B는 바이트 길이가 같고 오프셋이 밀리지 않는다.
이 전제 위에서만 diff가 성립한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def diff_regions(a: bytes, b: bytes) -> list[tuple[int, int]]:
    """a와 b가 다른 바이트를 이어붙여 연속 구간 목록으로 묶는다. end는 배제 경계다."""
    regions: list[tuple[int, int]] = []
    n = len(a)
    i = 0
    while i < n:
        if a[i] != b[i]:
            start = i
            while i < n and a[i] != b[i]:
                i += 1
            regions.append((start, i))
        else:
            i += 1
    return regions


@dataclass(frozen=True)
class DiffOutcome:
    """diff_files()의 결과. ok가 False면 5-1절 1~2단계에서 실패했다는 뜻이다."""

    ok: bool
    region: tuple[int, int] | None
    reason: str | None
    all_regions: list[tuple[int, int]] = field(default_factory=list)


def diff_files(path_a: str | Path, path_b: str | Path) -> DiffOutcome:
    """SPEC 5-1절 1~2단계를 그대로 수행한다.

    1. 길이 확인 — 다르면 즉시 실패 (구조 불변 전제 위반).
    2. 차이 구간 추출 — 구간이 정확히 하나가 아니면 실패로 보고한다. 추측해서 진행하지 않는다.
    """
    data_a = Path(path_a).read_bytes()
    data_b = Path(path_b).read_bytes()

    if len(data_a) != len(data_b):
        return DiffOutcome(False, None, "length_mismatch")

    regions = diff_regions(data_a, data_b)

    if len(regions) == 0:
        return DiffOutcome(False, None, "no_diff", regions)
    if len(regions) > 1:
        return DiffOutcome(False, None, "scattered_diff", regions)

    return DiffOutcome(True, regions[0], None, regions)


CANDIDATE_SIZES: tuple[int, ...] = (2, 4, 8)


def candidate_slices(
    region: tuple[int, int], sizes: tuple[int, ...] = CANDIDATE_SIZES
) -> list[tuple[int, int]]:
    """diff 구간을 포함하는 후보 (offset, size) 슬라이스를 모두 열거한다. SPEC 5-1절 3단계.

    size가 diff 구간 길이보다 작으면 애초에 구간을 담을 수 없으므로 제외한다.
    남은 size에 대해서는, 슬라이스가 diff 구간 전체를 덮으면서 diff 구간 밖으로
    벗어나도 되는 오프셋을 전부 만든다 — 값의 앞/뒤에 안 변한 바이트가 섞여 있을 수 있어서다.
    """
    lo, hi = region
    length = hi - lo
    slices: list[tuple[int, int]] = []
    for size in sizes:
        if size < length:
            continue
        start_off = max(0, hi - size)
        end_off = lo
        for off in range(start_off, end_off + 1):
            slices.append((off, size))
    return slices


def discover_sets(samples_dir: Path = SAMPLES_DIR) -> list[str]:
    """samples/ 아래 setNN_a.bin이 있는 set_id를 오름차순으로 찾는다."""
    return sorted(p.stem[:-2] for p in samples_dir.glob("*_a.bin"))


def _print_table(samples_dir: Path = SAMPLES_DIR) -> None:
    print(f"{'set':<8}{'구간':<18}{'길이':>6}  결과")
    for set_id in discover_sets(samples_dir):
        path_a = samples_dir / f"{set_id}_a.bin"
        path_b = samples_dir / f"{set_id}_b.bin"
        outcome = diff_files(path_a, path_b)
        if outcome.ok:
            lo, hi = outcome.region
            print(f"{set_id:<8}0x{lo:05X}~0x{hi:05X}{hi - lo:>6}  OK")
        else:
            print(f"{set_id:<8}{'-':<18}{'-':>6}  실패: {outcome.reason}")


if __name__ == "__main__":
    _print_table()
