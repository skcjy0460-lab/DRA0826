import streamlit as st

from utils.history import report_data_to_csv_bytes, csv_bytes_to_report_data
from utils.state import init_state

init_state()

st.title("🔁 이력 비교 (전일 대비)")
st.info(
    "이 앱은 개인정보 보호를 위해 서버에 병원 데이터를 저장하지 않습니다. "
    "대신 오늘 데이터를 CSV로 내려받아 두었다가, 다음 근무일에 업로드하면 "
    "전일 대비 증감을 보고서에 자동으로 표시해드립니다.",
    icon="🔒",
)

st.subheader("① 오늘자 데이터 저장하기")
data = st.session_state.report_data
csv_bytes = report_data_to_csv_bytes(data)
hospital = data["meta"].get("hospital_name") or "hospital"
date_str = str(data["meta"].get("report_date"))
st.download_button(
    "⬇️ 오늘자 데이터 CSV로 저장",
    data=csv_bytes,
    file_name=f"report_data_{hospital}_{date_str}.csv".replace(" ", "_"),
    mime="text/csv",
)

st.divider()
st.subheader("② 이전 보고서 불러오기 (비교용)")
prev_file = st.file_uploader("이전에 저장한 CSV 파일 업로드", type=["csv"], key="prev_csv")
if prev_file is not None:
    if st.button("불러와서 비교 활성화", type="primary"):
        try:
            prev_data = csv_bytes_to_report_data(prev_file.getvalue())
            st.session_state.prev_report = prev_data
            st.success(
                f"{prev_data['meta'].get('report_date', '이전')}자 데이터를 불러왔습니다. "
                "'보고서 생성' 화면에서 증감 비교가 표시됩니다."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"불러오기 실패: {exc}")

if st.session_state.prev_report:
    st.caption(f"현재 비교 기준: {st.session_state.prev_report['meta'].get('report_date')}")
    if st.button("비교 데이터 초기화"):
        st.session_state.prev_report = None
        st.rerun()
