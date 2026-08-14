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


# renew로 초기화됨 (이전 설비 버전의 PARAMS는 backups/renew-2026-08-14/tools/sample_params.py에 있다).
# 새 설비(스키마) 버전의 파라미터를 data-gen이 여기에 채운다. dtype은 골고루 섞는다.
PARAMS: list[Param] = []
