import datetime as dt
from decimal import Decimal

import streamlit as st

from utils.calculations import compute_totals, outpatient_breakdown_sum, to_decimal
from utils.state import init_state

init_state()

st.title("📝 일일보고서 데이터 입력")
st.caption("수기로 직접 입력하거나, 좌측 메뉴의 '파일 업로드'에서 PDF/이미지/엑셀을 올려 자동 추출할 수 있습니다.")

data = st.session_state.report_data

with st.container(border=True):
    st.subheader("기본 정보")
    c1, c2, c3 = st.columns(3)
    with c1:
        data["meta"]["report_date"] = st.date_input(
            "보고 일자", value=data["meta"].get("report_date", dt.date.today())
        )
    with c2:
        data["meta"]["hospital_name"] = st.text_input(
            "병원명", value=data["meta"].get("hospital_name", "")
        )
    with c3:
        data["meta"]["writer"] = st.text_input("작성자", value=data["meta"].get("writer", ""))

with st.container(border=True):
    st.subheader("① 외래 인원 현황")
    st.caption("외래 TOTAL과 세부 항목(신환/초진/재진/미산정/순수재원)의 합이 다르면 하단에 경고가 표시됩니다.")
    op = data["outpatient"]
    c1, c2, c3 = st.columns(3)
    with c1:
        op["total"] = st.number_input("외래 TOTAL (명)", min_value=0, step=1, value=int(op.get("total", 0)))
        op["new_patient"] = st.number_input("신환환자 (명)", min_value=0, step=1, value=int(op.get("new_patient", 0)))
    with c2:
        op["first_visit"] = st.number_input("초진환자 (명)", min_value=0, step=1, value=int(op.get("first_visit", 0)))
        op["revisit"] = st.number_input("재진환자 (명)", min_value=0, step=1, value=int(op.get("revisit", 0)))
    with c3:
        op["unclassified"] = st.number_input("미산정환자 (명)", min_value=0, step=1, value=int(op.get("unclassified", 0)))
        op["pure_census"] = st.number_input("순수재원환자 (명)", min_value=0, step=1, value=int(op.get("pure_census", 0)))

    breakdown = outpatient_breakdown_sum(op)
    if breakdown != op["total"]:
        st.warning(f"세부 항목 합계는 {breakdown:,}명인데, 외래 TOTAL은 {op['total']:,}명입니다. 확인해주세요.")
    else:
        st.success(f"세부 항목 합계가 외래 TOTAL과 일치합니다. ({breakdown:,}명)")

with st.container(border=True):
    st.subheader("② 입원 / 퇴원 현황")
    ad = data["admission"]
    c1, c2, c3 = st.columns(3)
    with c1:
        ad["admitted_today"] = st.number_input(
            "당일 입원 (명)", min_value=0, step=1, value=int(ad.get("admitted_today", 0))
        )
    with c2:
        ad["discharged_today"] = st.number_input(
            "당일 퇴원 (명)", min_value=0, step=1, value=int(ad.get("discharged_today", 0))
        )
    with c3:
        ad["current_census"] = st.number_input(
            "현재 재원환자수 (선택, 명)", min_value=0, step=1, value=int(ad.get("current_census", 0))
        )

with st.container(border=True):
    st.subheader("③ 수납금 내역")
    pay = data["payment"]
    c1, c2 = st.columns(2)
    with c1:
        pay["cash"] = st.number_input(
            "현금 (원)", min_value=0, step=1000, value=int(to_decimal(pay.get("cash", 0)))
        )
        pay["unpaid"] = st.number_input(
            "미수금 (원)", min_value=0, step=1000, value=int(to_decimal(pay.get("unpaid", 0)))
        )
        pay["rounding_cut"] = st.number_input(
            "절사 (원)", min_value=0, step=100, value=int(to_decimal(pay.get("rounding_cut", 0)))
        )
    with c2:
        pay["card"] = st.number_input(
            "카드 (원)", min_value=0, step=1000, value=int(to_decimal(pay.get("card", 0)))
        )
        pay["non_covered"] = st.number_input(
            "비급여 (원, 참고용)", min_value=0, step=1000, value=int(to_decimal(pay.get("non_covered", 0)))
        )

with st.container(border=True):
    st.subheader("④ 할인금 내역")
    disc = data["discount"]
    c1, c2 = st.columns(2)
    with c1:
        disc["exemption"] = st.number_input(
            "감면 (원)", min_value=0, step=1000, value=int(to_decimal(disc.get("exemption", 0)))
        )
    with c2:
        disc["discount"] = st.number_input(
            "할인 (원)", min_value=0, step=1000, value=int(to_decimal(disc.get("discount", 0)))
        )

with st.container(border=True):
    st.subheader("⑤ 수술 및 시술 현황")
    st.caption("전체 건수를 입력하고, 필요하면 아래에서 수술/시술명별로 세부 건수·금액을 추가하세요.")
    proc = data["procedures"]
    c1, c2 = st.columns(2)
    with c1:
        proc["surgery_total"] = st.number_input(
            "수술 건수 (전체, 건)", min_value=0, step=1, value=int(proc.get("surgery_total", 0))
        )
    with c2:
        proc["procedure_total"] = st.number_input(
            "시술 건수 (전체, 건)", min_value=0, step=1, value=int(proc.get("procedure_total", 0))
        )

    st.markdown("**세부 내역 (선택)**")
    for idx, item in enumerate(proc["items"]):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            item["name"] = st.text_input(
                "수술/시술명", value=item.get("name", ""), key=f"proc_name_{idx}"
            )
        with c2:
            item["count"] = st.number_input(
                "건수", min_value=0, step=1, value=int(item.get("count", 0) or 0), key=f"proc_count_{idx}"
            )
        with c3:
            item["amount"] = st.number_input(
                "금액 (원, 선택)",
                min_value=0,
                step=1000,
                value=int(to_decimal(item.get("amount", 0))),
                key=f"proc_amt_{idx}",
            )
        with c4:
            if st.button("삭제", key=f"proc_del_{idx}"):
                proc["items"].pop(idx)
                st.rerun()

    if st.button("+ 수술/시술 항목 추가"):
        proc["items"].append({"name": "", "count": 0, "amount": 0})
        st.rerun()

with st.container(border=True):
    st.subheader("⑥ 기타 항목 (선택 - 병원별 커스텀 항목)")
    st.caption("예: 에스테틱, 시재, 검진 매출 등 병원마다 다른 항목을 자유롭게 추가하세요.")

    for idx, item in enumerate(data["custom_items"]):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            item["label"] = st.text_input("항목명", value=item.get("label", ""), key=f"custom_label_{idx}")
        with c2:
            item["category"] = st.selectbox(
                "구분",
                ["인원", "금액"],
                index=0 if item.get("category", "금액") == "인원" else 1,
                key=f"custom_cat_{idx}",
            )
        with c3:
            item["amount"] = st.number_input(
                "값", min_value=0, step=1, value=int(to_decimal(item.get("amount", 0))), key=f"custom_amt_{idx}"
            )
        with c4:
            if st.button("삭제", key=f"custom_del_{idx}"):
                data["custom_items"].pop(idx)
                st.rerun()

    if st.button("+ 항목 추가"):
        data["custom_items"].append({"label": "", "category": "금액", "amount": 0})
        st.rerun()

st.divider()
totals = compute_totals(data)
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 수납액 (현금+카드+기타)", f"{int(totals['total_received']):,}원")
c2.metric("할인 합계", f"{int(totals['total_discount']):,}원")
c3.metric("최종 합계 (절사 반영)", f"{int(totals['grand_total']):,}원")
c4.metric("수술+시술 건수", f"{int(totals['procedures_total_count']):,}건")

st.info("입력을 마쳤으면 좌측 메뉴의 **'보고서 생성'**으로 이동해 미리보기 및 다운로드를 진행하세요.")
