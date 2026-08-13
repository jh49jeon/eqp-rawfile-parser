#!/usr/bin/env python3
"""Phase 0 — 테스트용 샘플 raw file(A/B 세트) 생성기. SPEC 7절.

설비 recipe 바이너리를 흉내 낸다. 각 세트는 파라미터 하나만 값이 다른
A/B 한 쌍이고, 나머지 바이트는 완전히 동일하다.

설계상 지켜야 하는 것 세 가지 (SPEC 7절):

1. 배경을 0으로 채우지 않는다. 0으로 채우면 변경 구간이 유일한 비영 영역이
   되어 schemaMaker의 탐색이 무의미해진다.
2. 바꾼 값과 같은 바이트열을 파일 다른 곳에도 심는다(decoy). 없으면
   "값으로 검색하면 바로 찾아진다"가 되어 A/B diff를 쓸 이유가 사라진다.
3. change.yaml에 dtype·offset·endian을 적지 않는다. 적으면 schemaMaker가
   정답을 훔쳐보게 되어 추론 알고리즘이 검증 가치를 잃는다.

samples/ 는 hook으로 보호되므로 이 스크립트는 Bash로 직접 실행한다.
"""

from __future__ import annotations

import argparse
import random
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

FILE_SIZE = 256 * 1024
SEED = 20260813
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# 값이 놓이는 구간. 앞쪽 1KB는 헤더처럼 두고 건드리지 않는다.
PARAM_REGION = (0x0400, FILE_SIZE - 0x0400)


@dataclass(frozen=True)
class Param:
    """한 세트에서 변경할 파라미터. dtype/endian은 정답이며 샘플 밖으로 새지 않는다."""

    set_id: str
    unit: str
    name: str
    dtype: str
    endian: str
    before: str  # CIM 화면에 보이는 표기 그대로
    after: str
    offset: int


# dtype이 골고루 섞이도록 배정한다. set08은 0 -> 1 로 모호성 규칙을 시험한다.
PARAMS: list[Param] = [
    Param("set01", "COT", "chuck_temp", "float32", "little", "25.0", "30.0", 0x1000),
    Param("set02", "BAKE", "bake_time", "int32", "little", "60", "90", 0x2440),
    Param("set03", "COT", "spin_rpm", "int32", "big", "1500", "1800", 0x38C0),
    Param("set04", "DEV", "nozzle_id", "int16", "little", "3", "5", 0x4A02),
    Param("set05", "TRACK", "recipe_ts", "timestamp", "little", "1735689600", "1767225600", 0x5C10),
    Param("set06", "COT", "exhaust_flow", "float64", "little", "12.75", "14.5", 0x6E08),
    Param("set07", "COT", "edge_bead_width", "float32", "big", "2.0", "2.5", 0x8004),
    Param("set08", "TRACK", "auto_purge_enable", "int32", "little", "0", "1", 0x9220),
    Param("set09", "BAKE", "hotplate_temp", "float32", "little", "110.0", "115.0", 0xA418),
    Param("set10", "SCAN", "scan_speed", "int16", "big", "200", "240", 0xB606),
]

_FORMATS = {
    ("int16", "little"): "<h",
    ("int16", "big"): ">h",
    ("int32", "little"): "<i",
    ("int32", "big"): ">i",
    ("int64", "little"): "<q",
    ("int64", "big"): ">q",
    ("float32", "little"): "<f",
    ("float32", "big"): ">f",
    ("float64", "little"): "<d",
    ("float64", "big"): ">d",
    ("timestamp", "little"): "<I",
    ("timestamp", "big"): ">I",
}


def encode(value: str, dtype: str, endian: str) -> bytes:
    """화면 표기 문자열을 바이트로 인코딩한다."""
    fmt = _FORMATS[(dtype, endian)]
    number = float(value) if dtype.startswith("float") else int(value)
    return struct.pack(fmt, number)


def build_background(rng: random.Random) -> bytearray:
    """그럴듯한 recipe 데이터를 흉내 낸 배경. A와 B가 공유한다."""
    buf = bytearray(FILE_SIZE)

    # 헤더 비슷한 앞부분 — 매직과 버전, 나머지는 잡값.
    buf[0:4] = b"PTRK"
    buf[4:8] = struct.pack("<I", 3)
    for i in range(8, 0x0400):
        buf[i] = rng.randrange(256)

    # 파라미터 영역: int32 / float32 / timestamp 를 섞어 4바이트 단위로 채운다.
    for off in range(PARAM_REGION[0], PARAM_REGION[1], 4):
        kind = rng.random()
        if kind < 0.45:
            buf[off:off + 4] = struct.pack("<i", rng.randrange(-5000, 20000))
        elif kind < 0.85:
            buf[off:off + 4] = struct.pack("<f", rng.uniform(0.0, 500.0))
        else:
            buf[off:off + 4] = struct.pack("<I", rng.randrange(1_600_000_000, 1_800_000_000))

    # 꼬리 부분도 0으로 남기지 않는다.
    for i in range(PARAM_REGION[1], FILE_SIZE):
        buf[i] = rng.randrange(256)

    return buf


def plant_decoys(buf: bytearray, param: Param, rng: random.Random) -> list[int]:
    """바꾼 값과 같은 바이트열을 다른 위치에도 심는다 (SPEC 7절).

    값으로 파일을 검색하면 여러 곳이 걸리므로, 변경 위치를 특정하려면
    A/B diff가 반드시 필요해진다.
    """
    encoded_before = encode(param.before, param.dtype, param.endian)
    encoded_after = encode(param.after, param.dtype, param.endian)
    size = len(encoded_before)

    planted: list[int] = []
    for payload in (encoded_before, encoded_after):
        for _ in range(2):
            while True:
                spot = rng.randrange(PARAM_REGION[0], PARAM_REGION[1] - size)
                spot -= spot % 2
                # 변경 지점과 겹치면 A/B가 두 곳에서 달라진다.
                if abs(spot - param.offset) < 64:
                    continue
                if any(abs(spot - p) < 64 for p in planted):
                    continue
                break
            buf[spot:spot + size] = payload
            planted.append(spot)
    return planted


def write_set(param: Param, force: bool) -> None:
    # 세트마다 배경을 따로 만들되 시드는 고정해 재현 가능하게 한다.
    rng = random.Random(f"{SEED}-{param.set_id}")

    buf = build_background(rng)
    plant_decoys(buf, param, rng)

    encoded_before = encode(param.before, param.dtype, param.endian)
    encoded_after = encode(param.after, param.dtype, param.endian)
    size = len(encoded_before)

    file_a = bytearray(buf)
    file_a[param.offset:param.offset + size] = encoded_before
    file_b = bytearray(buf)
    file_b[param.offset:param.offset + size] = encoded_after

    targets = {
        SAMPLES_DIR / f"{param.set_id}_a.bin": bytes(file_a),
        SAMPLES_DIR / f"{param.set_id}_b.bin": bytes(file_b),
    }

    # change.yaml — 사람이 줄 수 있는 것만 담는다 (SPEC 5절).
    # dtype·offset·endian은 의도적으로 뺀다.
    change = (
        f"set: {param.set_id}\n"
        f"unit: {param.unit}\n"
        f"name: {param.name}\n"
        f'before: "{param.before}"\n'
        f'after: "{param.after}"\n'
    )
    targets[SAMPLES_DIR / f"{param.set_id}_change.yaml"] = change.encode("utf-8")

    for path, payload in targets.items():
        if path.exists() and not force:
            raise SystemExit(
                f"이미 있는 파일입니다: {path.name}\n"
                "샘플을 덮어쓰면 지금까지 적립한 schema.json의 근거가 무효가 됩니다.\n"
                "정말 다시 만들려면 --force 를 주세요."
            )
        path.write_bytes(payload)


def verify_set(param: Param) -> None:
    """SPEC 7절 Phase 0 판정 조건을 스크립트 자체적으로 확인한다."""
    data_a = (SAMPLES_DIR / f"{param.set_id}_a.bin").read_bytes()
    data_b = (SAMPLES_DIR / f"{param.set_id}_b.bin").read_bytes()

    assert len(data_a) == len(data_b) == FILE_SIZE, f"{param.set_id}: 길이 불일치"

    diff = [i for i, (x, y) in enumerate(zip(data_a, data_b)) if x != y]
    assert diff, f"{param.set_id}: 차이가 없습니다"

    lo, hi = diff[0], diff[-1] + 1
    assert hi - lo <= 8, f"{param.set_id}: 차이 구간이 흩어져 있습니다 ({lo}~{hi})"
    assert lo >= param.offset and hi <= param.offset + 8, f"{param.set_id}: 차이 위치가 예상 밖입니다"

    size = len(encode(param.before, param.dtype, param.endian))
    fmt = _FORMATS[(param.dtype, param.endian)]
    got_a = struct.unpack(fmt, data_a[param.offset:param.offset + size])[0]
    got_b = struct.unpack(fmt, data_b[param.offset:param.offset + size])[0]

    if param.dtype.startswith("float"):
        expected_a, expected_b = float(param.before), float(param.after)
        ok = abs(got_a - expected_a) < 1e-4 and abs(got_b - expected_b) < 1e-4
    else:
        ok = got_a == int(param.before) and got_b == int(param.after)
    assert ok, f"{param.set_id}: 디코딩 값 불일치 ({got_a} / {got_b})"

    print(f"  {param.set_id}  {param.unit:<6} {param.name:<18} "
          f"{param.before:>12} -> {param.after:<12} @ 0x{lo:05X} ({hi - lo}B)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 샘플 A/B 세트 생성")
    ap.add_argument("--force", action="store_true", help="기존 샘플을 덮어쓴다")
    args = ap.parse_args()

    SAMPLES_DIR.mkdir(exist_ok=True)

    for param in PARAMS:
        write_set(param, args.force)

    print(f"{len(PARAMS)}개 세트 생성 완료 ({FILE_SIZE // 1024}KB/파일)\n")
    print("검증:")
    for param in PARAMS:
        verify_set(param)

    print("\n모든 세트가 Phase 0 판정 조건을 만족합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
