"""세션 상태 스키마 정의 및 초기화.

이 앱은 병원 데이터를 서버에 저장하지 않습니다(무료 배포/개인정보 보호 목적).
모든 데이터는 브라우저 세션(st.session_state) 안에서만 유지되며,
새로고침 시 초기화됩니다. 대신 '이력 비교' 화면에서 CSV로 저장/불러오기하여
전일 대비 비교가 가능하도록 지원합니다.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Dict

import streamlit as st

DEFAULT_HOSPITAL_NAME = ""

def _decimal_default() -> Decimal:
    return Decimal("0")


def default_report_data() -> Dict[str, Any]:
    today = dt.date.today()
    return {
        "meta": {
            "report_date": today,
            "hospital_name": DEFAULT_HOSPITAL_NAME,
            "writer": "",
        },
        # 외래 내원 환자수 세분화
        "outpatient": {
            "total": 0,  # 외래 TOTAL
            "pure_census": 0,  # 순수재원환자
            "first_visit": 0,  # 초진환자
            "new_patient": 0,  # 신환환자
            "unclassified": 0,  # 미산정환자
            "revisit": 0,  # 재진환자
        },
        # 입원/퇴원 환자수
        "admission": {
            "admitted_today": 0,  # 당일 입원
            "discharged_today": 0,  # 당일 퇴원
            "current_census": 0,  # 현재 재원환자수 (선택)
        },
        # 수납금 내역
        "payment": {
            "cash": _decimal_default(),  # 현금
            "card": _decimal_default(),  # 카드
            "unpaid": _decimal_default(),  # 미수금
            "non_covered": _decimal_default(),  # 비급여 (참고용, 현금/카드에 이미 포함될 수 있음)
            "rounding_cut": _decimal_default(),  # 절사
        },
        # 할인금 내역
        "discount": {
            "exemption": _decimal_default(),  # 감면
            "discount": _decimal_default(),  # 할인
        },
        # 사용자 정의 항목 (병원마다 다른 항목 대응)
        "custom_items": [],  # [{"label": str, "amount": Decimal, "category": "인원"|"금액"}]
        "ai_comment": "",
        "ai_comment_model": "",
    }


def init_state() -> None:
    if "report_data" not in st.session_state:
        st.session_state.report_data = default_report_data()
    if "extracted_review" not in st.session_state:
        st.session_state.extracted_review = None  # 업로드 후 검토 대기중인 데이터
    if "prev_report" not in st.session_state:
        st.session_state.prev_report = None  # CSV로 불러온 이전 보고서(비교용)
    if "generated_html" not in st.session_state:
        st.session_state.generated_html = None


def reset_state() -> None:
    st.session_state.report_data = default_report_data()
    st.session_state.extracted_review = None
    st.session_state.generated_html = None
