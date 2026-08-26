import streamlit as st

from utils.file_extractor import extract_from_upload, merge_extracted_into_schema
from utils.state import init_state, default_report_data

init_state()

st.title("📤 파일 업로드 자동 추출")
st.caption(
    "기존에 작성하던 PDF/이미지(JPG,PNG)/엑셀 보고서를 그대로 업로드하면, "
    "AI가 항목을 읽어 자동으로 입력해드립니다. 병원마다 양식이 달라도 괜찮습니다."
)

st.warning(
    "⚠️ 자동 추출 결과는 반드시 아래에서 **검토 후 '반영하기'**를 눌러야 실제 보고서에 적용됩니다. "
    "AI가 숫자를 잘못 읽을 수 있으니, 원본과 대조해주세요.",
    icon="⚠️",
)

uploaded = st.file_uploader(
    "보고서 파일 업로드 (PDF, JPG, PNG, XLS, XLSX)",
    type=["pdf", "jpg", "jpeg", "png", "xls", "xlsx"],
)

if uploaded is not None:
    if st.button("AI로 데이터 추출하기", type="primary"):
        with st.spinner("파일을 분석하고 있습니다..."):
            try:
                extracted = extract_from_upload(uploaded)
                st.session_state.extracted_review = extracted
                st.success(
                    f"추출 완료 (사용 모델: {extracted.get('_used_model', '알 수 없음')}). "
                    "아래에서 값을 검토해주세요."
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"추출 중 오류가 발생했습니다: {exc}")

if st.session_state.extracted_review:
    extracted = st.session_state.extracted_review
    st.divider()
    st.subheader("추출 결과 검토 및 수정")

    review = {
        "outpatient": dict(extracted.get("outpatient", {})),
        "admission": dict(extracted.get("admission", {})),
        "payment": dict(extracted.get("payment", {})),
        "discount": dict(extracted.get("discount", {})),
    }

    with st.container(border=True):
        st.markdown("**외래 인원**")
        c1, c2, c3 = st.columns(3)
        op = review["outpatient"]
        with c1:
            op["total"] = st.number_input("외래 TOTAL", value=int(op.get("total", 0) or 0), key="rv_op_total")
            op["new_patient"] = st.number_input("신환", value=int(op.get("new_patient", 0) or 0), key="rv_op_new")
        with c2:
            op["first_visit"] = st.number_input("초진", value=int(op.get("first_visit", 0) or 0), key="rv_op_first")
            op["revisit"] = st.number_input("재진", value=int(op.get("revisit", 0) or 0), key="rv_op_revisit")
        with c3:
            op["unclassified"] = st.number_input(
                "미산정", value=int(op.get("unclassified", 0) or 0), key="rv_op_unclass"
            )
            op["pure_census"] = st.number_input(
                "순수재원", value=int(op.get("pure_census", 0) or 0), key="rv_op_pure"
            )

    with st.container(border=True):
        st.markdown("**입원 / 퇴원**")
        c1, c2, c3 = st.columns(3)
        ad = review["admission"]
        with c1:
            ad["admitted_today"] = st.number_input(
                "당일 입원", value=int(ad.get("admitted_today", 0) or 0), key="rv_ad_in"
            )
        with c2:
            ad["discharged_today"] = st.number_input(
                "당일 퇴원", value=int(ad.get("discharged_today", 0) or 0), key="rv_ad_out"
            )
        with c3:
            ad["current_census"] = st.number_input(
                "현재 재원", value=int(ad.get("current_census", 0) or 0), key="rv_ad_census"
            )

    with st.container(border=True):
        st.markdown("**수납 / 할인**")
        c1, c2 = st.columns(2)
        pay = review["payment"]
        disc = review["discount"]
        with c1:
            pay["cash"] = st.number_input("현금", value=int(pay.get("cash", 0) or 0), key="rv_pay_cash")
            pay["card"] = st.number_input("카드", value=int(pay.get("card", 0) or 0), key="rv_pay_card")
            pay["unpaid"] = st.number_input("미수금", value=int(pay.get("unpaid", 0) or 0), key="rv_pay_unpaid")
        with c2:
            pay["non_covered"] = st.number_input(
                "비급여", value=int(pay.get("non_covered", 0) or 0), key="rv_pay_nc"
            )
            pay["rounding_cut"] = st.number_input(
                "절사", value=int(pay.get("rounding_cut", 0) or 0), key="rv_pay_round"
            )
            disc["exemption"] = st.number_input(
                "감면", value=int(disc.get("exemption", 0) or 0), key="rv_disc_exempt"
            )
            disc["discount"] = st.number_input(
                "할인", value=int(disc.get("discount", 0) or 0), key="rv_disc_disc"
            )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ 이 값을 보고서에 반영하기", type="primary"):
            base = st.session_state.report_data
            merged = merge_extracted_into_schema(review, base)
            merged["meta"] = base["meta"]
            merged["custom_items"] = base.get("custom_items", [])
            st.session_state.report_data = merged
            st.session_state.extracted_review = None
            st.success("반영 완료! '데이터 입력' 또는 '보고서 생성' 화면에서 확인하세요.")
            st.rerun()
    with c2:
        if st.button("취소"):
            st.session_state.extracted_review = None
            st.rerun()
