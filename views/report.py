import streamlit as st

from utils.calculations import compute_totals
from utils.gemini_client import generate_management_comment
from utils.report_template import build_report_html
from utils.state import init_state

init_state()

st.title("📄 보고서 생성")

data = st.session_state.report_data
totals = compute_totals(data)

prev_totals = None
if st.session_state.prev_report:
    prev_totals = compute_totals(st.session_state.prev_report)
    st.caption("✅ 전일 보고서가 불러와져 있어 증감(▲▼)이 함께 표시됩니다. ('이력 비교' 메뉴에서 불러오기)")
else:
    st.caption("ℹ️ 전일 보고서를 불러오면 증감 비교가 함께 표시됩니다. ('이력 비교' 메뉴 이용)")

c1, c2 = st.columns([1, 1])
with c1:
    use_ai_comment = st.toggle("AI 경영 브리핑 코멘트 포함", value=True)
with c2:
    if st.button("🔄 코멘트 새로 생성", disabled=not use_ai_comment):
        with st.spinner("AI가 코멘트를 작성하고 있습니다..."):
            try:
                summary_for_ai = {
                    "외래_total": data["outpatient"]["total"],
                    "입원": data["admission"]["admitted_today"],
                    "퇴원": data["admission"]["discharged_today"],
                    "총_수납액": str(totals["total_received"]),
                    "미수금": str(totals["unpaid"]),
                    "할인_합계": str(totals["total_discount"]),
                }
                diff_for_ai = None
                if prev_totals:
                    diff_for_ai = {
                        "전일_총수납액": str(prev_totals["total_received"]),
                        "전일_미수금": str(prev_totals["unpaid"]),
                    }
                result = generate_management_comment(summary_for_ai, diff_for_ai)
                data["ai_comment"] = result["comment"]
                data["ai_comment_model"] = result["model"]
            except Exception as exc:  # noqa: BLE001
                st.error(f"코멘트 생성 실패: {exc}")

if data.get("ai_comment"):
    with st.expander("생성된 코멘트 미리보기 / 수정", expanded=True):
        data["ai_comment"] = st.text_area(
            "코멘트 (직접 수정 가능)", value=data["ai_comment"], height=100
        )
        if data.get("ai_comment_model"):
            st.caption(f"사용 모델: {data['ai_comment_model']}")

comment_to_use = data.get("ai_comment", "") if use_ai_comment else ""

html = build_report_html(data, totals, prev_totals=prev_totals, ai_comment=comment_to_use)
st.session_state.generated_html = html

st.divider()
st.subheader("미리보기 (A4 인쇄 최적화)")
st.iframe(html, height=900)

st.divider()
hospital = data["meta"].get("hospital_name") or "hospital"
date_str = str(data["meta"].get("report_date"))
filename = f"daily_report_{hospital}_{date_str}.html".replace(" ", "_")

st.download_button(
    "⬇️ HTML 보고서 다운로드 (열어서 Ctrl+P로 PDF 저장 가능)",
    data=html.encode("utf-8"),
    file_name=filename,
    mime="text/html",
    type="primary",
)
st.caption(
    "다운로드한 HTML 파일을 브라우저에서 열고 인쇄(Ctrl+P) → 'PDF로 저장'을 선택하면 "
    "A4 규격에 맞춘 보고서 PDF를 바로 얻을 수 있습니다."
)
