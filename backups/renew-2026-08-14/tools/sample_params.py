#!/usr/bin/env python3
"""gen_samples.py가 쓰는 Param 정의와 PARAMS 목록. SPEC 7절.

gen_samples.py 본체(생성 로직)와 분리했다 — 세트가 늘어날수록 PARAMS만 계속
길어지는데, 로직 파일에 같이 두면 300줄 제한을 쉽게 넘는다. dtype/offset/endian은
정답이며 샘플 밖으로 새지 않는다(SPEC 7절 3항).
"""

from __future__ import annotations

from dataclasses import dataclass


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


# renew로 초기화됨 (이전 설비 버전의 PARAMS는 backups/renew-2026-08-13/tools/gen_samples.py에 있다).
# 새 설비(스키마) 버전의 파라미터를 data-gen이 여기에 채운다. dtype은 골고루 섞는다.
PARAMS: list[Param] = [
    Param("set01", "COT", "chuck_temp", "float32", "little", "25.0", "30.0", 0x2000),
    Param("set02", "BAKE", "plate_temp", "int32", "little", "110", "120", 0x3000),
    Param("set03", "TRACK", "wafer_count", "int16", "little", "0", "1", 0x4000),
    Param("set04", "ETCH", "rf_power", "float64", "little", "850.5", "900.25", 0x5000),
    Param("set05", "CMP", "run_ts", "timestamp", "little", "1700000000", "1700003600", 0x6000),
    Param("set06", "IMPL", "dose_level", "int64", "little", "1200000", "1500000", 0x7000),
    Param("set07", "DIFF", "furnace_temp", "float32", "little", "950.0", "975.5", 0x8000),
    Param("set08", "METRO", "cd_target", "float32", "big", "45.2", "44.8", 0x9000),
    Param("set09", "SCAN", "focus_offset", "int32", "big", "-120", "-95", 0xA000),
    Param("set10", "DEV", "dev_time", "int16", "little", "60", "75", 0xB000),
    Param("set11", "COT", "spin_speed", "int32", "little", "2500", "3000", 0xC000),
    Param("set12", "BAKE", "cycle_count", "int16", "big", "3", "4", 0xD000),
    Param("set13", "TRACK", "align_x", "float64", "little", "0.125", "0.250", 0xE000),
    Param("set14", "ETCH", "gas_flow", "int32", "little", "150", "180", 0xF000),
    Param("set15", "CMP", "pad_pressure", "float32", "little", "3.5", "4.2", 0x10000),
    Param("set16", "IMPL", "cal_ts", "timestamp", "big", "1690000000", "1690086400", 0x11000),
    Param("set17", "DIFF", "step_time", "int64", "little", "3600", "7200", 0x12000),
    Param("set18", "METRO", "overlay_err", "float64", "big", "-0.015", "0.008", 0x13000),
    Param("set19", "SCAN", "exposure_dose", "int16", "little", "-100", "-50", 0x14000),
    Param("set20", "DEV", "puddle_time", "int32", "big", "45", "50", 0x15000),
    # 사이클 2 시작 (새 설비 버전) — set21부터. 기존 세트 구간(0x2000~0x15FFF)과
    # 최소 64바이트 이상 떨어뜨려 0x16000부터 이어 붙인다.
    Param("set21", "COT", "nozzle_temp", "float32", "little", "42.0", "45.5", 0x16000),
    Param("set22", "BAKE", "hotplate_id", "int16", "little", "2", "3", 0x16400),
    Param("set23", "TRACK", "lot_seq", "int32", "big", "1001", "1002", 0x16800),
    Param("set24", "ETCH", "chamber_pressure", "float64", "little", "12.75", "13.10", 0x16C00),
    Param("set25", "CMP", "slurry_ts", "timestamp", "little", "1701000000", "1701003600", 0x17000),
    Param("set26", "IMPL", "beam_current", "int64", "little", "800000", "950000", 0x17400),
    Param("set27", "DIFF", "anneal_temp", "float32", "big", "1050.0", "1075.25", 0x17800),
    Param("set28", "METRO", "thickness_target", "float32", "little", "12.4", "12.8", 0x17C00),
    Param("set29", "SCAN", "z_offset", "int32", "little", "-40", "-25", 0x18000),
    Param("set30", "DEV", "rinse_time", "int16", "big", "30", "40", 0x18400),
    Param("set31", "COT", "ramp_rate", "int32", "little", "500", "650", 0x18800),
    Param("set32", "BAKE", "exhaust_flow", "int16", "little", "12", "15", 0x18C00),
    Param("set33", "TRACK", "align_y", "float64", "big", "0.075", "0.150", 0x19000),
    Param("set34", "ETCH", "endpoint_ts", "timestamp", "big", "1701500000", "1701586400", 0x19400),
    Param("set35", "CMP", "downforce", "float64", "little", "5.2", "6.0", 0x19800),
    # 사이클 3 시작 — set36부터. set35 구간(0x19800)과 64바이트 이상 떨어뜨려
    # 0x1A000부터 이어 붙인다.
    Param("set36", "COT", "dispense_volume", "float32", "little", "1.8", "2.1", 0x1A000),
    Param("set37", "BAKE", "vac_level", "int16", "little", "700", "650", 0x1A400),
    Param("set38", "TRACK", "arm_position", "int32", "big", "220", "260", 0x1A800),
    Param("set39", "ETCH", "bias_voltage", "float64", "little", "-135.5", "-140.25", 0x1AC00),
    Param("set40", "CMP", "conditioner_ts", "timestamp", "little", "1702000000", "1702003600", 0x1B000),
    Param("set41", "IMPL", "tilt_angle", "int64", "little", "7", "15", 0x1B400),
    Param("set42", "DIFF", "ramp_down_temp", "float32", "big", "600.0", "580.5", 0x1B800),
    Param("set43", "METRO", "sigma_target", "float32", "little", "2.1", "1.8", 0x1BC00),
    Param("set44", "SCAN", "reticle_id", "int32", "little", "305", "306", 0x1C000),
    Param("set45", "DEV", "spray_time", "int16", "big", "20", "25", 0x1C400),
    Param("set46", "COT", "edge_bead_width", "int32", "little", "3", "4", 0x1C800),
    Param("set47", "BAKE", "n2_purge_flow", "int16", "little", "8", "10", 0x1CC00),
    Param("set48", "TRACK", "align_z", "float64", "big", "0.045", "0.090", 0x1D000),
    Param("set49", "ETCH", "endpoint_cal_ts", "timestamp", "big", "1702500000", "1702586400", 0x1D400),
    Param("set50", "CMP", "removal_rate", "float64", "little", "450.0", "512.75", 0x1D800),
    # 사이클 3 마지막 라운드 — set51부터. set50 구간(0x1D800)과 64바이트 이상
    # 떨어뜨려 0x1E000부터 이어 붙인다.
    Param("set51", "COT", "prewet_time", "int16", "little", "5", "8", 0x1E000),
    Param("set52", "BAKE", "chill_temp", "float32", "little", "23.0", "20.5", 0x1E400),
    Param("set53", "TRACK", "handoff_delay", "int32", "big", "150", "175", 0x1E800),
    Param("set54", "ETCH", "coil_power", "float64", "little", "600.25", "625.75", 0x1EC00),
    Param("set55", "CMP", "dress_ts", "timestamp", "little", "1703000000", "1703003600", 0x1F000),
    Param("set56", "IMPL", "scan_speed", "int64", "little", "2200", "2500", 0x1F400),
    Param("set57", "DIFF", "gas_ratio", "float32", "big", "0.65", "0.72", 0x1F800),
    Param("set58", "METRO", "haze_limit", "float32", "little", "0.08", "0.06", 0x1FC00),
    Param("set59", "SCAN", "grid_offset", "int32", "little", "-15", "-8", 0x20000),
    Param("set60", "DEV", "purge_time", "int16", "big", "10", "14", 0x20400),
    Param("set61", "COT", "backside_rinse", "int32", "little", "2", "3", 0x20800),
    Param("set62", "BAKE", "cooldown_rate", "int16", "little", "5", "7", 0x20C00),
    Param("set63", "TRACK", "buffer_slot", "float64", "big", "0.020", "0.035", 0x21000),
    Param("set64", "ETCH", "strike_ts", "timestamp", "big", "1703500000", "1703586400", 0x21400),
    Param("set65", "CMP", "polish_uniformity", "float64", "little", "1.15", "0.92", 0x21800),
    Param("set66", "IMPL", "dose_count", "int64", "big", "3200000", "3450000", 0x21C00),
    Param("set67", "IMPL", "last_calib_ts", "timestamp", "little", "1712000000", "1712345678", 0x22000),
]
