"""서버에 데이터를 저장하지 않는 대신, CSV 다운로드/업로드로 전일 대비 비교를 지원.

사용 흐름:
1. 오늘 보고서 작성 완료 -> '오늘자 데이터 CSV로 저장' 다운로드
2. 다음 날 -> 어제 저장한 CSV를 '이전 보고서 불러오기'에 업로드
3. 앱이 두 데이터를 비교해 증감(▲▼)을 보고서에 자동 반영
"""
from __future__ import annotations

import io
import json
from decimal import Decimal
from typing import Any, Dict, Optional

import pandas as pd


def _json_default(o):
    if isinstance(o, Decimal):
        return str(o)
    from datetime import date

    if isinstance(o, date):
        return o.isoformat()
    return str(o)


def report_data_to_csv_bytes(report_data: Dict[str, Any]) -> bytes:
    """report_data를 단일행 CSV로 직렬화 (각 셀에 JSON 문자열 저장하여 구조 보존)."""
    flat = {}
    for section in ("meta", "outpatient", "admission", "payment", "discount", "procedures"):
        flat[section] = json.dumps(report_data[section], default=_json_default, ensure_ascii=False)
    flat["custom_items"] = json.dumps(
        report_data.get("custom_items", []), default=_json_default, ensure_ascii=False
    )
    df = pd.DataFrame([flat])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")


def csv_bytes_to_report_data(file_bytes: bytes) -> Optional[Dict[str, Any]]:
    df = pd.read_csv(io.BytesIO(file_bytes))
    if df.empty:
        return None
    row = df.iloc[0]
    data = {}
    for section in ("meta", "outpatient", "admission", "payment", "discount"):
        data[section] = json.loads(row[section])
    if "procedures" in row and pd.notna(row["procedures"]):
        data["procedures"] = json.loads(row["procedures"])
    else:
        data["procedures"] = {"surgery_total": 0, "procedure_total": 0, "items": []}
    data["custom_items"] = json.loads(row.get("custom_items", "[]"))
    return data
