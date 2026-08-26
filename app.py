import streamlit as st

st.set_page_config(
    page_title="병원 일일보고서 자동생성",
    page_icon="🏥",
    layout="wide",
)

input_page = st.Page("views/input.py", title="데이터 입력", icon="📝", default=True)
upload_page = st.Page("views/upload.py", title="파일 업로드 (AI 자동추출)", icon="📤")
report_page = st.Page("views/report.py", title="보고서 생성", icon="📄")
compare_page = st.Page("views/compare.py", title="이력 비교", icon="🔁")

pg = st.navigation(
    {
        "일일보고서": [input_page, upload_page, report_page, compare_page],
    }
)

with st.sidebar:
    st.markdown("### 🏥 병원 일일보고서 자동생성")
    st.caption("주식회사 메디엄 · 무료 버전")
    st.divider()
    st.caption(
        "1️⃣ 데이터 입력 또는 파일 업로드\n\n"
        "2️⃣ 보고서 생성에서 미리보기 및 AI 코멘트\n\n"
        "3️⃣ HTML 다운로드 → 인쇄(Ctrl+P)로 PDF 저장"
    )
    st.divider()
    st.caption("⚠️ 데이터는 서버에 저장되지 않으며, 새로고침 시 초기화됩니다.")

pg.run()
