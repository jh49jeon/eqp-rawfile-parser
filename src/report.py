"""파싱 결과 HTML 리포트. SPEC.md#9, backlog LB-120 (희망 사항 — 핵심 아님).

parse()의 반환값을 그대로 표로 옮긴다. 새로운 판정 로직은 없다 — provisional 항목만
표에서 구분되게 표시한다.
"""

from __future__ import annotations

import html
from pathlib import Path

from parser import parse

_ROW_TEMPLATE = """    <tr class="{row_class}">
      <td>{name}</td>
      <td>{unit}</td>
      <td>{value}</td>
      <td>{dtype}</td>
      <td>0x{offset:05X}</td>
      <td>{flag}</td>
    </tr>"""

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>파싱 결과 리포트 — {source}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; margin: 2rem; color: #1a1a1a; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.7rem; text-align: left; }}
  th {{ background: #f0f0f0; }}
  tr.provisional {{ background: #fff6d8; }}
  .badge {{ display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }}
  .badge-provisional {{ background: #f5c518; color: #1a1a1a; }}
  caption {{ text-align: left; margin-bottom: 0.5rem; color: #555; }}
</style>
</head>
<body>
<h1>파싱 결과 리포트</h1>
<table>
  <caption>{source} · {count}건 (provisional {provisional_count}건)</caption>
  <thead>
    <tr><th>name</th><th>unit</th><th>value</th><th>dtype</th><th>offset</th><th>status</th></tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>
</body>
</html>
"""


def _escape(value: object) -> str:
    return html.escape(str(value))


def render_report(records: list[dict], source: str) -> str:
    """parse()의 반환값을 HTML 표로 렌더링한다. provisional 항목은 행·배지로 구분된다."""
    rows = []
    for r in records:
        is_provisional = bool(r.get("provisional"))
        rows.append(
            _ROW_TEMPLATE.format(
                row_class="provisional" if is_provisional else "",
                name=_escape(r["name"]),
                unit=_escape(r["unit"]),
                value=_escape(r["value"]),
                dtype=_escape(r["dtype"]),
                offset=r["offset"],
                flag='<span class="badge badge-provisional">provisional</span>' if is_provisional else "confirmed",
            )
        )
    return _PAGE_TEMPLATE.format(
        source=_escape(source),
        count=len(records),
        provisional_count=sum(1 for r in records if r.get("provisional")),
        rows="\n".join(rows) if rows else '    <tr><td colspan="6">알아낸 파라미터가 없습니다.</td></tr>',
    )


def write_report(bin_path: str, schema: dict, out_path: str = "report.html") -> str:
    records = parse(bin_path, schema)
    html_text = render_report(records, source=bin_path)
    Path(out_path).write_text(html_text, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print("사용법: python src/report.py <bin파일> <schema.json> [출력.html]")
        raise SystemExit(1)

    schema_path = Path(sys.argv[2])
    schema_data = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {"parameters": []}
    out = sys.argv[3] if len(sys.argv) > 3 else "report.html"
    written = write_report(sys.argv[1], schema_data, out)
    print(f"작성됨: {written}")
