"""dtype/endian/size 조합의 struct 인코딩. parser.py와 schema_maker.py가 함께 쓴다.

SPEC 5-1절 3단계 후보 집합: int16/int32/int64/float32/float64/timestamp(epoch32,epoch64)
× (little, big). timestamp는 부호 없는 정수로 저장되고 size로 epoch32(4바이트)/epoch64(8바이트)가
갈린다 — dtype 이름 자체는 폭을 담지 않는다.
"""

from __future__ import annotations

import struct

_STRUCT_CODE = {
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
}

DTYPE_SIZES = {
    "int16": (2,),
    "int32": (4,),
    "int64": (8,),
    "float32": (4,),
    "float64": (8,),
    "timestamp": (4, 8),
}


def format_for(dtype: str, endian: str, size: int) -> str:
    if dtype == "timestamp":
        if size not in (4, 8):
            raise ValueError(f"timestamp는 4 또는 8바이트만 지원한다 (size={size})")
        code = "I" if size == 4 else "Q"
        prefix = "<" if endian == "little" else ">"
        return prefix + code
    if size not in DTYPE_SIZES.get(dtype, ()):
        raise ValueError(f"{dtype}는 size={size}를 지원하지 않는다")
    return _STRUCT_CODE[(dtype, endian)]


def decode(data: bytes, dtype: str, endian: str, size: int) -> int | float:
    fmt = format_for(dtype, endian, size)
    return struct.unpack(fmt, data[:size])[0]


def encode(value: int | float, dtype: str, endian: str, size: int) -> bytes:
    fmt = format_for(dtype, endian, size)
    return struct.pack(fmt, value)


def is_float_dtype(dtype: str) -> bool:
    return dtype.startswith("float")
