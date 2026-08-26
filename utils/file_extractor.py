"""업로드된 파일(PDF/JPG/PNG/XLS/XLSX)을 스키마 데이터로 변환."""
from __future__ import annotations

import io
from typing import Any, Dict, Optional

import pandas as pd

from . import gemini_client

MIME_MAP = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def excel_to_table_text(file_bytes: bytes) -> str:
    """엑셀의 모든 시트를 좌표 포함 텍스트로 변환 (레이아웃 자유형 대응)."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    chunks = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, header=None)
        chunks.append(f"[시트: {sheet_name}]")
        for r_idx, row in df.iterrows():
            for c_idx, val in enumerate(row):
                if pd.notna(val) and str(val).strip() != "":
                    col_letter = chr(65 + c_idx) if c_idx < 26 else str(c_idx)
                    chunks.append(f"{col_letter}{r_idx + 1}: {val}")
    return "\n".join(chunks)


def extract_from_upload(uploaded_file) -> Optional[Dict[str, Any]]:
    """Streamlit UploadedFile 객체를 받아 스키마 dict를 반환."""
    ext = _extension(uploaded_file.name)
    file_bytes = uploaded_file.getvalue()

    if ext in ("xlsx", "xls"):
        table_text = excel_to_table_text(file_bytes)
        if not table_text.strip():
            raise ValueError("엑셀 파일에서 읽을 수 있는 데이터를 찾지 못했습니다.")
        return gemini_client.extract_report_data_from_table_text(table_text)

    if ext in MIME_MAP:
        mime_type = MIME_MAP[ext]
        return gemini_client.extract_report_data_from_file(file_bytes, mime_type)

    raise ValueError(f"지원하지 않는 파일 형식입니다: .{ext}")


def merge_extracted_into_schema(extracted: Dict[str, Any], base_schema: Dict[str, Any]) -> Dict[str, Any]:
    """추출된 JSON을 기본 스키마 위에 안전하게 병합(누락 필드는 0/기존값 유지)."""
    import copy

    merged = copy.deepcopy(base_schema)
    for section in ("outpatient", "admission", "payment", "discount"):
        if section in extracted and isinstance(extracted[section], dict):
            for key, val in extracted[section].items():
                if key in merged[section]:
                    merged[section][key] = val

    if "procedures" in extracted and isinstance(extracted["procedures"], dict):
        proc = extracted["procedures"]
        merged["procedures"]["surgery_total"] = proc.get(
            "surgery_total", merged["procedures"]["surgery_total"]
        )
        merged["procedures"]["procedure_total"] = proc.get(
            "procedure_total", merged["procedures"]["procedure_total"]
        )
        items = proc.get("items", [])
        if isinstance(items, list):
            merged["procedures"]["items"] = [
                {
                    "name": it.get("name", ""),
                    "count": it.get("count", 0) or 0,
                    "amount": it.get("amount", 0) or 0,
                }
                for it in items
                if isinstance(it, dict)
            ]
    return merged
