# 병원 일일보고서 자동생성 (무료 버전)

원무과에서 매일 진료 마감 전 작성하는 일일보고서를 5~10분 이내로 끝낼 수 있도록 만든 Streamlit 앱입니다.

## 폴더 구조
```
daily_report_app/
├─ app.py                  # 메인 진입점 (st.navigation)
├─ requirements.txt
├─ .streamlit/
│   └─ secrets.toml.example
├─ utils/
│   ├─ state.py             # 세션 데이터 스키마
│   ├─ calculations.py      # 합계/증감 계산 (AI 미개입, 100% 결정론적)
│   ├─ gemini_client.py     # Gemini API 연동 + 모델 fallback 체인
│   ├─ file_extractor.py    # PDF/이미지/엑셀 → 구조화 데이터 추출
│   ├─ report_template.py   # A4 인쇄 최적화 HTML 보고서 템플릿
│   └─ history.py           # CSV 기반 전일 대비 비교
└─ views/
    ├─ input.py              # 수기 입력 화면
    ├─ upload.py             # 파일 업로드 + AI 자동추출 + 검토
    ├─ report.py             # 보고서 미리보기 / AI 코멘트 / 다운로드
    └─ compare.py            # 전일 대비 CSV 저장·불러오기
```

## 로컬 실행 방법
```bash
cd daily_report_app
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml 에 실제 GEMINI_API_KEY 입력
streamlit run app.py
```

## Streamlit Cloud(무료) 배포 방법
1. 이 폴더를 GitHub 저장소에 업로드 (한글 파일명은 이미 제거되어 있어 Windows/zip 인코딩 문제 없음)
2. https://share.streamlit.io 에서 New app → 저장소 선택 → Main file: `app.py`
3. App settings → Secrets 에 아래와 같이 입력
   ```
   GEMINI_API_KEY = "발급받은_키"
   ```
4. Deploy 후 게시판에 URL 링크만 공유하면 별도 설치 없이 누구나 사용 가능합니다.

## 핵심 설계 원칙 (왜 이렇게 만들었는지)
- **금액 계산에는 AI를 쓰지 않습니다.** 현금/카드/미수금/비급여/절사/감면/할인의 합계는 전부
  `utils/calculations.py`에서 Decimal 연산으로 고정 계산합니다. Gemini는 이미 계산이 끝난
  숫자를 바탕으로 "경영 브리핑 코멘트" 문장만 작성하며, 새로운 숫자를 만들어내지 않도록
  프롬프트에서 명시적으로 제한했습니다.
- **파일 업로드 추출 결과는 반드시 사람이 검토합니다.** AI가 OCR/추출한 값은 바로 반영되지
  않고, `views/upload.py`의 검토 폼을 거쳐 사용자가 확인·수정한 뒤 "반영하기"를 눌러야
  실제 보고서 데이터에 들어갑니다.
- **서버에 병원 데이터를 저장하지 않습니다.** 무료로 공개 배포되는 도구이므로, 모든 데이터는
  브라우저 세션 안에서만 유지됩니다. 대신 전일 대비 비교가 필요한 경우 CSV를 다운로드해서
  다음날 업로드하는 방식으로 지원합니다(`views/compare.py`).
- **A4 인쇄 최적화.** `report_template.py`의 CSS에 `@page { size: A4; }`와
  `page-break-inside: avoid`를 각 섹션에 적용해, 표나 카드가 페이지 경계에서 잘리지 않고
  통째로 다음 페이지로 넘어가도록 처리했습니다. weasyprint로 PDF 변환 테스트를 통해
  실제로 섹션이 잘리지 않는 것을 확인했습니다.
- **모델 fallback 체인.** `gemini-3.6-flash → gemini-3.5-flash-lite → gemini-2.5-flash →
  gemini-2.0-flash` 순서로 시도하며, 앞 모델이 오류/과부하이면 자동으로 다음 모델로 넘어갑니다.

## 향후 확장 아이디어 (필요시 요청해주세요)
- Supabase 등을 연동한 서버 측 이력 저장(단, 개인정보 처리방침 필요)
- 여러 날짜 데이터를 모아 주간/월간 추이 그래프 제공
- 병원별 커스텀 템플릿 저장 기능
