#!/usr/bin/env python3
"""Phase 0 — 테스트용 샘플 raw file(A/B 세트) 생성기. SPEC 7절.

설비 recipe 바이너리를 흉내 낸다. 각 세트는 파라미터 하나만 값이 다른
A/B 한 쌍이고, 나머지 바이트는 완전히 동일하다.

모든 세트는 같은 설비·같은 스키마의 파일이라는 전제 하에, 배경(diff 대상이 아닌
영역)을 하나만 만들어 모든 세트가 공유한다 — 그래야 여러 세트를 적립해 만든
schema.json으로 아무 파일이나 하나 파싱해도 나머지 필드가 세트마다 제각각인
난수가 아니라 같은 레시피의 일관된 값으로 보인다.

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
    Param("set11", "ETCH", "rf_power", "int64", "little", "1000000", "2000000", 0xC800),
    Param("set12", "ETCH", "gas_flow", "int64", "big", "500", "750", 0xD900),
    Param("set13", "CMP", "pad_pressure", "float64", "big", "3.14", "6.28", 0xEA00),
    Param("set14", "CMP", "polish_end_ts", "timestamp", "big", "1735689600", "1767225600", 0xFB00),
    Param("set15", "IMPL", "dose_rate", "float32", "little", "1.5", "3.0", 0x10C00),
    Param("set16", "IMPL", "beam_current", "int16", "little", "12", "18", 0x12000),
    Param("set17", "DIFF", "furnace_pressure", "float64", "big", "0.85", "1.2", 0x14000),
    Param("set18", "DIFF", "anneal_ts", "timestamp", "little", "1735689600", "1767225600", 0x16000),
    Param("set19", "METRO", "film_thickness_count", "int64", "big", "300000", "450000", 0x18000),
    Param("set20", "METRO", "overlay_shift", "float32", "little", "0.02", "0.05", 0x1A000),
    # set21~set30 — 기존 provisional 항목에 대한 두 번째 관측(같은 name/offset,
    # 다른 before/after). LB-123: 재추론으로 후보를 더 좁힐 수 있는지 시험한다.
    # int16-vs-int32처럼 진짜 인코딩 바이트 자체가 겹치는 모호성은 값 크기를
    # 16비트 범위 밖으로 키우면 깨진다. timestamp-vs-int32처럼 두 해석이 항상
    # 같은 비트 패턴을 내는 모호성은 숫자 증거만으로는 원리적으로 안 풀린다.
    Param("set21", "BAKE", "bake_time", "int32", "little", "45000", "60000", 0x2440),
    Param("set22", "COT", "spin_rpm", "int32", "big", "40000", "50000", 0x38C0),
    Param("set23", "TRACK", "recipe_ts", "timestamp", "little", "1700000000", "1750000000", 0x5C10),
    Param("set24", "TRACK", "auto_purge_enable", "int32", "little", "1", "0", 0x9220),
    Param("set25", "ETCH", "rf_power", "int64", "little", "3000000000", "4000000000", 0xC800),
    Param("set26", "ETCH", "gas_flow", "int64", "big", "3000000000", "4000000000", 0xD900),
    Param("set27", "CMP", "polish_end_ts", "timestamp", "big", "1700000000", "1750000000", 0xFB00),
    Param("set28", "IMPL", "beam_current", "int16", "little", "20000", "30000", 0x12000),
    Param("set29", "DIFF", "anneal_ts", "timestamp", "little", "1700000000", "1750000000", 0x16000),
    Param("set30", "METRO", "film_thickness_count", "int64", "big", "3000000000", "4000000000", 0x18000),
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


def build_shared_background() -> bytes:
    """모든 세트가 공유하는 단 하나의 배경. 같은 설비의 같은 스키마를 흉내 낸다.

    세트마다 배경을 따로 만들면, 한 세트에서 안 바뀐 자리(=다른 세트의 실제
    파라미터 값)가 세트마다 제각각인 난수가 되어버린다. schema.json을 여러 세트에
    걸쳐 적립한 뒤 실제 파일 하나를 파싱해보면 그 세트에서 다루지 않은 필드가 전부
    쓰레기값으로 보이는 문제가 여기서 생긴다. 배경을 SEED 하나로 한 번만 만들어
    모든 세트가 그대로 복사해 쓰면, 어느 세트의 파일을 파싱하더라도 나머지 필드가
    같은 값(=같은 레시피의 그 필드)으로 일관되게 보인다.
    """
    rng = random.Random(SEED)
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

    return bytes(buf)


def plant_decoys(
    buf: bytearray, param: Param, rng: random.Random, avoid_offsets: list[int]
) -> list[int]:
    """바꾼 값과 같은 바이트열을 다른 위치에도 심는다 (SPEC 7절).

    값으로 파일을 검색하면 여러 곳이 걸리므로, 변경 위치를 특정하려면
    A/B diff가 반드시 필요해진다. avoid_offsets에는 이 세트뿐 아니라 다른 모든
    세트의 실제 파라미터 offset도 넣는다 — 배경을 세트 간에 공유하므로, 다른
    파라미터의 자리에 decoy를 심으면 그 파라미터 값이 이 파일에서만 달라져
    "모든 세트가 같은 스키마를 공유한다"는 전제가 깨진다.
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
                if any(abs(spot - off) < 64 for off in avoid_offsets):
                    continue
                if any(abs(spot - p) < 64 for p in planted):
                    continue
                break
            buf[spot:spot + size] = payload
            planted.append(spot)
    return planted


def write_set(background: bytes, param: Param, force: bool) -> None:
    # decoy 위치만 세트마다 다르게 흩뿌린다. 배경 자체는 모든 세트가 공유한다.
    rng = random.Random(f"{SEED}-decoy-{param.set_id}")

    buf = bytearray(background)
    other_offsets = [p.offset for p in PARAMS if p.set_id != param.set_id]
    plant_decoys(buf, param, rng, other_offsets)

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

    background = build_shared_background()
    for param in PARAMS:
        write_set(background, param, args.force)

    print(f"{len(PARAMS)}개 세트 생성 완료 ({FILE_SIZE // 1024}KB/파일)\n")
    print("검증:")
    for param in PARAMS:
        verify_set(param)

    print("\n모든 세트가 Phase 0 판정 조건을 만족합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
