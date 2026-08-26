"""Gemini API 연동.

- 모델 fallback 체인: gemini-3.6-flash -> gemini-3.5-flash-lite -> gemini-2.5-flash -> gemini-2.0-flash
- 용도 1: 업로드된 PDF/이미지/엑셀에서 일일보고서 항목을 구조화 JSON으로 추출
- 용도 2: 확정된 숫자(계산 완료본)를 바탕으로 경영진 보고용 코멘트 문장 생성

주의: 이 모듈은 절대 표에 들어갈 '숫자'를 만들어내지 않습니다.
추출된 숫자는 반드시 사용자 검토(수정 가능한 폼)를 거친 뒤에만 반영됩니다.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import streamlit as st

MODEL_FALLBACK_CHAIN: List[str] = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

EXTRACTION_SCHEMA_HINT = {
    "outpatient": {
        "total": "외래 총 내원 환자수(정수)",
        "pure_census": "순수재원환자 수(정수)",
        "first_visit": "초진환자 수(정수)",
        "new_patient": "신환환자 수(정수)",
        "unclassified": "미산정환자 수(정수)",
        "revisit": "재진환자 수(정수)",
    },
    "admission": {
        "admitted_today": "당일 입원 환자수(정수)",
        "discharged_today": "당일 퇴원 환자수(정수)",
        "current_census": "현재 재원환자수(정수, 없으면 0)",
    },
    "payment": {
        "cash": "현금 수납액(숫자, 콤마/원 제외)",
        "card": "카드 수납액(숫자)",
        "unpaid": "미수금(숫자)",
        "non_covered": "비급여 금액(숫자)",
        "rounding_cut": "절사 금액(숫자)",
    },
    "discount": {
        "exemption": "감면 금액(숫자)",
        "discount": "할인 금액(숫자)",
    },
}


def _get_client():
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _try_models(client, contents, config=None):
    """fallback 체인을 순서대로 시도. 성공한 응답과 사용된 모델명을 반환."""
    last_error = None
    for model_name in MODEL_FALLBACK_CHAIN:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            return response, model_name
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError(f"모든 Gemini 모델 호출 실패: {last_error}")


def extract_report_data_from_file(
    file_bytes: bytes, mime_type: str, extra_text: str = ""
) -> Optional[Dict[str, Any]]:
    """업로드된 파일(이미지/PDF/엑셀 텍스트)에서 보고서 항목을 구조화 추출."""
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY가 설정되어 있지 않습니다. .streamlit/secrets.toml을 확인해주세요."
        )

    from google.genai import types

    prompt = f"""다음은 한국 병원 원무과의 일일보고서 원본 자료입니다.
아래 스키마에 맞춰 값을 추출해서 JSON으로만 응답하세요. 설명, 마크다운 코드블록 금지.
값을 찾을 수 없으면 0으로 채우세요. 숫자는 콤마/원 단위 없이 순수 숫자로만 반환하세요.

스키마: {json.dumps(EXTRACTION_SCHEMA_HINT, ensure_ascii=False)}

{extra_text}
"""

    parts = [types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt]

    config = types.GenerateContentConfig(response_mime_type="application/json")

    response, used_model = _try_models(client, parts, config=config)
    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)
    data["_used_model"] = used_model
    return data


def extract_report_data_from_table_text(table_text: str) -> Optional[Dict[str, Any]]:
    """엑셀/CSV에서 추출한 표 텍스트(레이아웃이 병원마다 다름)를 스키마에 매핑."""
    client = _get_client()
    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY가 설정되어 있지 않습니다. .streamlit/secrets.toml을 확인해주세요."
        )

    from google.genai import types

    prompt = f"""다음은 병원 원무과 엑셀 일일보고서에서 추출한 셀 내용입니다.
병원마다 표 레이아웃이 다르니, 셀 텍스트의 라벨(예: '현금', '카드', '외래', '입원', '신환' 등)을
의미로 파악해서 아래 스키마 JSON으로만 응답하세요. 설명/코드블록 금지.
값을 찾을 수 없으면 0으로 채우세요.

스키마: {json.dumps(EXTRACTION_SCHEMA_HINT, ensure_ascii=False)}

원본 셀 데이터:
{table_text}
"""
    config = types.GenerateContentConfig(response_mime_type="application/json")
    response, used_model = _try_models(client, [prompt], config=config)
    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)
    data["_used_model"] = used_model
    return data


def generate_management_comment(
    computed_summary: Dict[str, Any], diff_summary: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """확정된 숫자를 바탕으로 원장/재무팀 보고용 코멘트 문장 생성.

    이 함수에는 이미 계산이 끝난 숫자만 전달하며, 모델은 문장만 작성합니다.
    """
    client = _get_client()
    if client is None:
        return {"comment": "", "model": ""}

    diff_text = json.dumps(diff_summary, ensure_ascii=False, default=str) if diff_summary else "없음(전일 데이터 미제공)"

    prompt = f"""아래는 오늘자 병원 원무과 일일보고서의 확정된 수치 요약입니다.
이 숫자를 그대로 인용하여, 병원장/재무팀이 읽을 짧고 전문적인 '경영 브리핑 코멘트'를
3~4문장, 한국어 존댓말로 작성하세요.
- 절대 새로운 숫자를 만들어내지 마세요. 제공된 숫자만 언급하세요.
- 과장된 수식어 대신 담백하고 신뢰감 있는 톤을 사용하세요.
- 전일 대비 데이터가 있으면 증감 추세를 한 문장 포함하세요.
- 마크다운, 불릿 없이 자연스러운 문단으로 작성하세요.

[확정 수치 요약]
{json.dumps(computed_summary, ensure_ascii=False, default=str)}

[전일 대비 데이터]
{diff_text}
"""
    from google.genai import types

    response, used_model = _try_models(client, [prompt])
    return {"comment": response.text.strip(), "model": used_model}
