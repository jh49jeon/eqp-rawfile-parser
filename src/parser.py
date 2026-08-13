"""SPEC.md 3절 — 호출 규약이 고정된 곳. Tester가 이 시그니처만 믿고 테스트를 쓴다."""

from __future__ import annotations

from pathlib import Path

from codec import decode

USED_STATUSES = ("confirmed", "provisional")


def parse(path: str, schema: dict) -> list[dict]:
    """알려진 파라미터만 추출한 평탄한 레코드 리스트를 반환한다.

    schema['parameters'] 중 status가 confirmed/provisional인 항목만 쓴다.
    disputed·deprecated는 쓰지 않는다 (SPEC 4-1절).
    """
    data = Path(path).read_bytes()
    records: list[dict] = []

    for param in schema.get("parameters", []):
        status = param.get("status")
        if status not in USED_STATUSES:
            continue

        offset = param["offset"]
        size = param["size"]
        value = decode(data[offset:offset + size], param["dtype"], param["endian"], size)

        record = {
            "name": param["name"],
            "unit": param["unit"],
            "value": value,
            "dtype": param["dtype"],
            "offset": offset,
            "table": param.get("table"),
            "row": param.get("row"),
            "column": param.get("column"),
        }
        if status == "provisional":
            record["provisional"] = True
        records.append(record)

    records.sort(key=lambda r: r["offset"])
    return records


def _print_table(path: str, schema: dict) -> None:
    records = parse(path, schema)
    if not records:
        print("알아낸 파라미터가 없습니다.")
        return
    print(f"{'name':<20}{'unit':<8}{'value':<16}{'dtype':<10}offset")
    for r in records:
        flag = " (provisional)" if r.get("provisional") else ""
        print(f"{r['name']:<20}{r['unit']:<8}{str(r['value']):<16}{r['dtype']:<10}0x{r['offset']:05X}{flag}")


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 3:
        print("사용법: python src/parser.py <bin파일> <schema.json>")
        raise SystemExit(1)

    schema_path = Path(sys.argv[2])
    schema_data = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {"parameters": []}
    _print_table(sys.argv[1], schema_data)
