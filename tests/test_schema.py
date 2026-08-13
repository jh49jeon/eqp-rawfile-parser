"""Phase 1 불변 조건 테스트.

SPEC.md 3절(parse() 호출 규약)과 4절(schema.json 불변 조건)을 다룬다.

주의: tester는 schema.json을 직접 열어 오프셋 겹침을 계산하지 않는다.
schema는 parse()에 넘기기 위해 json.load로만 읽고, 그 값 자체에는 assertion을 걸지 않는다.
이 테스트는 parse(path, schema)의 **반환값**만 검사한다:
  - 반환된 레코드들의 name이 중복되지 않는다 (4절 "name이 전체에서 유일하다"의
    관측 가능한 결과 — 같은 이름이 두 레코드로 안 나온다)
  - 레코드가 offset 오름차순으로 정렬되어 있다 (3절 "레코드 순서는 offset 오름차순")
  - 각 레코드가 3절에서 정한 8개 필드를 모두 갖는다
  - name · unit이 문자열이고, offset이 int다
"""
import glob
import json
import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
SCHEMA_PATH = os.path.join(ROOT_DIR, "schema.json")

sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from parser import parse  # noqa: E402

REQUIRED_FIELDS = {"name", "unit", "value", "dtype", "offset", "table", "row", "column"}


def _discover_sets():
    a_files = sorted(glob.glob(os.path.join(SAMPLES_DIR, "set*_a.bin")))
    return [os.path.basename(p)[: -len("_a.bin")] for p in a_files]


SET_NAMES = _discover_sets()


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(params=SET_NAMES)
def set_name(request):
    return request.param


def test_parse_returns_list(schema, set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    assert isinstance(records, list)


def test_parse_records_have_required_fields(schema, set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    for record in records:
        assert REQUIRED_FIELDS.issubset(record.keys()), (
            f"{set_name}: 레코드에 필수 필드가 빠졌다: {record.keys()}"
        )


def test_parse_records_field_types(schema, set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    for record in records:
        assert isinstance(record["name"], str)
        assert isinstance(record["unit"], str)
        assert isinstance(record["dtype"], str)
        assert isinstance(record["offset"], int)
        assert isinstance(record["value"], (int, float, str))


def test_parse_records_no_duplicate_names(schema, set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    names = [r["name"] for r in records]
    assert len(names) == len(set(names)), (
        f"{set_name}: parse() 결과에 같은 name이 중복으로 나왔다: {names}"
    )


def test_parse_records_sorted_by_offset_ascending(schema, set_name):
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    records = parse(a_path, schema)
    offsets = [r["offset"] for r in records]
    assert offsets == sorted(offsets), (
        f"{set_name}: parse() 결과가 offset 오름차순이 아니다: {offsets}"
    )


def test_parse_no_duplicate_names_across_ab_pair(schema, set_name):
    """A와 B 각각의 파싱 결과 모두에서 name 유일성이 유지된다."""
    a_path = os.path.join(SAMPLES_DIR, f"{set_name}_a.bin")
    b_path = os.path.join(SAMPLES_DIR, f"{set_name}_b.bin")

    a_records = parse(a_path, schema)
    b_records = parse(b_path, schema)

    a_names = [r["name"] for r in a_records]
    b_names = [r["name"] for r in b_records]

    assert len(a_names) == len(set(a_names))
    assert len(b_names) == len(set(b_names))
