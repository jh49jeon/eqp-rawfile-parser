"""Phase 2 파싱 일치 테스트.

각 세트에 대해:
  - parse(a.bin, schema)에서 change.yaml의 name에 해당하는 value가 before와 같다
  - parse(b.bin, schema)에서 같은 name의 value가 after와 같다

기대값은 오직 samples/*_change.yaml에서만 가져온다.
schema는 parse()에 넘기기 위해 json.load로만 읽고 그 값 자체는 들여다보지 않는다.

값 문자열에 소수점이 있으면 float로, 없으면 int로 비교한다 (SPEC.md 5절).
부동소수는 math.isclose로 비교한다 (SPEC.md 5-1절).
"""
import glob
import json
import math
import os
import sys

import pytest
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
SCHEMA_PATH = os.path.join(ROOT_DIR, "schema.json")

sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from parser import parse  # noqa: E402


def _discover_change_files():
    return sorted(glob.glob(os.path.join(SAMPLES_DIR, "set*_change.yaml")))


CHANGE_FILES = _discover_change_files()


def _load_change(change_path):
    with open(change_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _coerce_expected(value_str: str):
    """change.yaml에 적힌 화면 표기 문자열을 비교용 파이썬 값으로 변환한다.

    소수점이 있으면 float, 없으면 int. 숫자로 변환할 수 없으면 문자열 그대로 둔다
    (예: timestamp가 문자열로 표기된 경우 등).
    """
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        return value_str


def _assert_value_matches(actual, expected):
    if isinstance(expected, float):
        assert isinstance(actual, (int, float)), f"expected float-like, got {type(actual)}: {actual!r}"
        assert math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6), (
            f"value mismatch: actual={actual!r} expected={expected!r}"
        )
    elif isinstance(expected, int):
        assert actual == expected, f"value mismatch: actual={actual!r} expected={expected!r}"
    else:
        assert actual == expected, f"value mismatch: actual={actual!r} expected={expected!r}"


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(params=CHANGE_FILES, ids=lambda p: os.path.basename(p))
def change(request):
    return _load_change(request.param)


def _find_record(records, name):
    matches = [r for r in records if r["name"] == name]
    assert len(matches) == 1, (
        f"parse() 결과에서 name={name!r}인 레코드가 정확히 하나여야 하는데 {len(matches)}개 발견"
    )
    return matches[0]


def test_at_least_one_change_statement_discovered():
    assert len(CHANGE_FILES) > 0, "samples/ 아래에서 setNN_change.yaml을 찾지 못했다"


def test_parse_before_matches_a(schema, change):
    set_name = change["set"]
    name = change["name"]
    expected_before = _coerce_expected(change["before"])

    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    record = _find_record(records, name)

    _assert_value_matches(record["value"], expected_before)


def test_parse_after_matches_b(schema, change):
    set_name = change["set"]
    name = change["name"]
    expected_after = _coerce_expected(change["after"])

    b_path = os.path.join(SAMPLES_DIR, f"{set_name}_b.bin")
    records = parse(b_path, schema)
    record = _find_record(records, name)

    _assert_value_matches(record["value"], expected_after)


def test_parse_unit_matches_change_statement(schema, change):
    """value 외에 unit도 change.yaml에서 선언한 값과 일치해야 한다."""
    set_name = change["set"]
    name = change["name"]
    expected_unit = change["unit"]

    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    record = _find_record(records, name)

    assert record["unit"] == expected_unit
