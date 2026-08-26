"""A4 인쇄에 최적화된 '공식 행정문서' 톤의 일일보고서 템플릿.

디자인 방향: 병원 원무과에서 실제로 다루는 결재 문서(품의서, 정산서)의 격식을
빌려와, 흔한 대시보드 카드 UI 대신 세리프 헤드라인 + 레저(장부) 스타일 표로
구성했다. 우측 상단 결재란(담당/실장/원장 도장란)이 이 문서의 시그니처
요소로, 실제 인쇄 후 결재에 바로 사용할 수 있도록 기능적으로도 의미가 있다.

- @page 규칙으로 A4 여백 고정, page-break 제어로 섹션이 페이지 경계에서
  잘리지 않도록 처리
- 잉크 네이비 + 무광 브라스 골드 + warm parchment 팔레트
- Noto Serif KR(제목/숫자) + Noto Sans KR(본문/표) 타이포 페어링
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Dict, Optional

from .calculations import compute_diff, fmt_won, outpatient_breakdown_sum

WEEKDAY_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _diff_text(diff: Optional[Decimal], pct: Optional[float], unit: str = "원") -> str:
    """배지(pill) 대신 절제된 텍스트형 증감 표기."""
    if diff is None:
        return ""
    diff = Decimal(diff)
    if diff > 0:
        cls, arrow = "diff-up", "▲"
    elif diff < 0:
        cls, arrow = "diff-down", "▼"
    else:
        cls, arrow = "diff-flat", "－"
    diff_str = fmt_won(abs(diff)) if unit == "원" else f"{abs(int(diff)):,}"
    pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
    return f'<span class="diff {cls}">{arrow} {diff_str}{unit}{pct_str}</span>'


def _stat(label: str, value: int, unit: str = "명") -> str:
    return f"""
    <div class="stat">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value:,}<span class="stat-unit">{unit}</span></div>
    </div>
    """


def _money_row(label: str, value: Decimal, note: str = "", total: bool = False, diff_html: str = "") -> str:
    cls = "ledger-row total-row" if total else "ledger-row"
    note_html = f'<span class="row-note">{note}</span>' if note else ""
    return f"""
    <tr class="{cls}">
        <td class="row-label">{label}{note_html}</td>
        <td class="row-value">{fmt_won(value)}<span class="won">원</span></td>
        <td class="row-diff">{diff_html}</td>
    </tr>
    """


def _grid_cell(label: str, value: Decimal, note: str = "", diff_html: str = "") -> str:
    note_html = f'<span class="row-note">{note}</span>' if note else ""
    diff_block = f'<div class="mc-diff">{diff_html}</div>' if diff_html else ""
    return f"""
    <div class="mc-col">
        <div class="mc-label">{label}{note_html}</div>
        <div class="mc-value">{fmt_won(value)}<span class="won">원</span></div>
        {diff_block}
    </div>
    """


def _money_grid(pairs) -> str:
    """pairs: [(left_cell_html, right_cell_html), ...] 2열 그리드로 렌더링."""
    rows_html = ""
    for left, right in pairs:
        rows_html += f'<div class="money-grid-row">{left}{right}</div>'
    return f'<div class="money-grid">{rows_html}</div>'


def build_report_html(
    report_data: Dict[str, Any],
    totals: Dict[str, Any],
    prev_totals: Optional[Dict[str, Any]] = None,
    ai_comment: str = "",
) -> str:
    meta = report_data["meta"]
    outpatient = report_data["outpatient"]
    admission = report_data["admission"]
    procedures = report_data.get("procedures", {"surgery_total": 0, "procedure_total": 0, "items": []})
    custom_items = report_data.get("custom_items", [])

    report_date = meta.get("report_date")
    if isinstance(report_date, str):
        date_str = report_date
        weekday_str = ""
        doc_no_date = report_date
    else:
        date_str = report_date.strftime("%Y년 %m월 %d일")
        weekday_str = WEEKDAY_KR[report_date.weekday()]
        doc_no_date = report_date.strftime("%Y%m%d")

    hospital_name = meta.get("hospital_name") or "OO병원"
    writer = meta.get("writer") or "-"
    doc_no = f"원무-{doc_no_date}"

    # ---- 인원 현황 스탯 스트립 ----
    outpatient_stats = "".join(
        [
            _stat("외래 TOTAL", outpatient.get("total", 0)),
            _stat("신환", outpatient.get("new_patient", 0)),
            _stat("초진", outpatient.get("first_visit", 0)),
            _stat("재진", outpatient.get("revisit", 0)),
            _stat("미산정", outpatient.get("unclassified", 0)),
            _stat("순수재원", outpatient.get("pure_census", 0)),
        ]
    )
    admission_stats = "".join(
        [
            _stat("당일 입원", admission.get("admitted_today", 0)),
            _stat("당일 퇴원", admission.get("discharged_today", 0)),
            _stat("현재 재원", admission.get("current_census", 0)),
        ]
    )

    breakdown_sum = outpatient_breakdown_sum(outpatient)
    mismatch_note = ""
    if breakdown_sum != outpatient.get("total", 0):
        mismatch_note = (
            f'<div class="note-warning">※ 세부 항목 합계({breakdown_sum:,}명)와 '
            f'외래 TOTAL({outpatient.get("total", 0):,}명)이 일치하지 않습니다. 입력값을 확인해주세요.</div>'
        )

    # ---- 수술/시술 ----
    proc_stats = "".join(
        [
            _stat("수술", procedures.get("surgery_total", 0), unit="건"),
            _stat("시술", procedures.get("procedure_total", 0), unit="건"),
        ]
    )
    proc_items = procedures.get("items", [])
    proc_items_html = ""
    if proc_items:
        rows = ""
        for it in proc_items:
            name = it.get("name", "")
            count = int(it.get("count", 0) or 0)
            amount = it.get("amount", 0) or 0
            amount_cell = f"{fmt_won(amount)}<span class='won'>원</span>" if amount else "&mdash;"
            rows += f"""
            <tr class="ledger-row">
                <td class="row-label">{name}</td>
                <td class="row-value" style="text-align:center;">{count:,}건</td>
                <td class="row-diff" style="text-align:right;">{amount_cell}</td>
            </tr>
            """
        proc_items_html = f"""
        <table class="ledger-table sub-table">
            <thead><tr>
                <td class="th-label">수술 / 시술명</td>
                <td class="th-value" style="text-align:center;">건수</td>
                <td class="th-diff" style="text-align:right;">금액</td>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    # ---- 전일 대비 ----
    def diff_for(key_path: str, unit="원") -> str:
        if prev_totals is None:
            return ""
        diff, pct = compute_diff(totals.get(key_path), prev_totals.get(key_path))
        return _diff_text(diff, pct, unit=unit)

    payment_pairs = [
        (
            _grid_cell("현금", totals["cash"], diff_html=diff_for("cash")),
            _grid_cell("카드", totals["card"], diff_html=diff_for("card")),
        ),
        (
            _grid_cell("미수금", totals["unpaid"], diff_html=diff_for("unpaid")),
            _grid_cell("비급여", totals["non_covered"], note="참고"),
        ),
        (
            _grid_cell("절사", totals["rounding_cut"]),
            _grid_cell("기타 항목 합계", totals["custom_amount_sum"]),
        ),
    ]
    payment_grid_html = _money_grid(payment_pairs)

    discount_pairs = [
        (
            _grid_cell("감면", totals["exemption"]),
            _grid_cell("할인", totals["discount"]),
        ),
    ]
    discount_grid_html = _money_grid(discount_pairs)
    discount_total_html = f"""
    <div class="ledger-total-row">
        <span class="lt-label">할인 합계</span>
        <span class="lt-value">{fmt_won(totals['total_discount'])}<span class="won">원</span></span>
    </div>
    """

    custom_count_items = [c for c in custom_items if c.get("category") == "인원"]
    custom_amount_items = [c for c in custom_items if c.get("category") == "금액"]

    custom_section_html = ""
    if custom_count_items or custom_amount_items:
        stats_html = "".join(
            _stat(item.get("label", ""), int(item.get("amount", 0) or 0)) for item in custom_count_items
        )
        stats_block = f'<div class="stat-strip">{stats_html}</div>' if custom_count_items else ""
        amount_rows = "".join(
            _money_row(item.get("label", ""), Decimal(str(item.get("amount", 0) or 0)))
            for item in custom_amount_items
        )
        amount_block = (
            f'<table class="ledger-table"><tbody>{amount_rows}</tbody></table>'
            if custom_amount_items
            else ""
        )
        custom_section_html = f"""
        <section class="report-section">
            <h2 class="section-title"><span class="marker"></span>기타 항목</h2>
            {stats_block}
            {amount_block}
        </section>
        """

    ai_comment_html = ""
    if ai_comment:
        ai_comment_html = f"""
        <section class="report-section ai-comment-section">
            <h2 class="section-title"><span class="marker"></span>경영 브리핑</h2>
            <p class="ai-comment-text">{ai_comment}</p>
        </section>
        """

    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{hospital_name} 일일보고서 {date_str}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    :root {{
        --ink: #14213c;
        --ink-soft: #2c3a57;
        --charcoal: #2a2a28;
        --gold: #96762c;
        --gold-deep: #7a5f22;
        --hairline: #d9d3c4;
        --panel: #faf8f3;
        --panel-border: #e6e0cf;
        --up: #a13c2e;
        --down: #2f4c74;
        --paper: #fffdf9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        color: var(--charcoal);
        margin: 0;
        background: #e9e6dd;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        word-break: keep-all;
        overflow-wrap: break-word;
    }}
    @page {{ size: A4; margin: 15mm 16mm; }}
    .page {{
        max-width: 780px;
        margin: 0 auto;
        padding: 10mm 4mm 6mm 4mm;
        background: var(--paper);
    }}
    @media screen {{
        body {{ padding: 24px 0; }}
        .page {{ box-shadow: 0 6px 30px rgba(20,33,60,0.12); }}
    }}

    /* ---------- 레터헤드 ---------- */
    .letterhead-bar {{
        height: 4px;
        background: linear-gradient(90deg, var(--ink) 0%, var(--gold) 55%, var(--ink) 100%);
        margin-bottom: 16px;
    }}
    .report-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 20px;
        padding-bottom: 14px;
        border-bottom: 2px solid var(--ink);
        margin-bottom: 22px;
    }}
    .title-block .eyebrow {{
        font-family: 'Noto Serif KR', serif;
        font-size: 10.5px;
        letter-spacing: 4px;
        color: var(--gold-deep);
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .title-block {{
        min-width: 0;
        flex: 1;
    }}
    .title-block h1 {{
        font-family: 'Noto Serif KR', serif;
        font-size: 21px;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: var(--ink);
        letter-spacing: 0.3px;
        line-height: 1.35;
    }}
    .title-block .doc-meta {{
        font-size: 11.5px;
        color: #6b6455;
        display: flex;
        flex-wrap: wrap;
        gap: 6px 14px;
    }}
    .title-block .doc-meta b {{ color: var(--ink-soft); font-weight: 600; }}

    /* ---------- 결재란 (시그니처 요소) ---------- */
    .approval-box {{
        border: 1px solid var(--ink);
        flex-shrink: 0;
    }}
    .approval-box .approval-title {{
        text-align: center;
        font-size: 10px;
        letter-spacing: 2px;
        padding: 3px 0;
        background: var(--ink);
        color: #f4efe1;
        font-weight: 600;
    }}
    .approval-cells {{
        display: flex;
    }}
    .approval-cell {{
        width: 25mm;
        border-right: 1px solid var(--hairline);
    }}
    .approval-cell:last-child {{ border-right: none; }}
    .approval-cell .role {{
        text-align: center;
        font-size: 10.5px;
        color: var(--ink-soft);
        font-weight: 600;
        padding: 4px 0;
        border-bottom: 1px solid var(--hairline);
        background: var(--panel);
    }}
    .approval-cell .stamp-space {{
        height: 17mm;
    }}

    /* ---------- 섹션 ---------- */
    .report-section {{
        margin-bottom: 20px;
        page-break-inside: avoid;
    }}
    .section-title {{
        display: flex;
        align-items: center;
        font-family: 'Noto Serif KR', serif;
        font-size: 14.5px;
        font-weight: 600;
        color: var(--ink);
        letter-spacing: 1px;
        margin: 0 0 10px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--hairline);
    }}
    .section-title .marker {{
        display: inline-block;
        width: 7px;
        height: 7px;
        background: var(--gold);
        margin-right: 8px;
        transform: rotate(45deg);
        flex-shrink: 0;
    }}

    /* ---------- 스탯 스트립 (카드 대신) ---------- */
    .stat-strip {{
        display: flex;
        border-top: 1px solid var(--panel-border);
        border-bottom: 1px solid var(--panel-border);
        background: var(--panel);
    }}
    .stat {{
        flex: 1;
        text-align: center;
        padding: 10px 4px;
        border-right: 1px solid var(--panel-border);
    }}
    .stat:last-child {{ border-right: none; }}
    .stat-label {{
        font-size: 10.5px;
        color: #7a7462;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}
    .stat-value {{
        font-family: 'Noto Serif KR', serif;
        font-size: 20px;
        font-weight: 700;
        color: var(--ink);
        font-variant-numeric: tabular-nums;
    }}
    .stat-value .stat-unit {{
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 11px;
        font-weight: 500;
        color: #8b8570;
        margin-left: 2px;
    }}
    .note-warning {{
        margin-top: 8px;
        font-size: 11.5px;
        color: var(--up);
        background: #fbf1ee;
        border-left: 3px solid var(--up);
        padding: 6px 10px;
    }}

    /* ---------- 레저(장부) 테이블 ---------- */
    table.ledger-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    table.ledger-table.sub-table {{
        margin-top: 10px;
        font-size: 12.5px;
    }}
    table.ledger-table thead td {{
        font-size: 10.5px;
        color: #8b8570;
        letter-spacing: 1px;
        border-bottom: 1px solid var(--ink);
        padding: 4px 10px 6px 0;
    }}
    tr.ledger-row {{
        border-bottom: 1px solid var(--hairline);
    }}
    tr.ledger-row td {{
        padding: 8px 10px 8px 0;
    }}
    .row-label {{
        color: var(--charcoal);
        width: 38%;
    }}
    .row-note {{
        font-size: 10px;
        color: #a39d89;
        margin-left: 6px;
    }}
    .row-value {{
        text-align: right;
        font-weight: 600;
        width: 32%;
        color: var(--ink);
        font-variant-numeric: tabular-nums;
        font-family: 'Noto Serif KR', serif;
    }}
    .row-value .won, .row-diff .won {{
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 11px;
        font-weight: 400;
        color: #8b8570;
        margin-left: 1px;
    }}
    .row-diff {{
        text-align: right;
        width: 30%;
        font-size: 11px;
    }}
    tr.total-row td {{
        border-top: 2px solid var(--gold);
        border-bottom: 2px solid var(--gold);
        background: var(--panel);
        font-weight: 700;
        padding-top: 9px;
        padding-bottom: 9px;
    }}
    tr.total-row .row-value {{ font-size: 15px; }}
    .diff {{ font-weight: 600; }}
    .diff-up {{ color: var(--up); }}
    .diff-down {{ color: var(--down); }}
    .diff-flat {{ color: #9a9484; }}

    /* ---------- 2열 금액 그리드 (수납금/할인금) ---------- */
    .money-grid {{
        border-top: 1px solid var(--panel-border);
    }}
    .money-grid-row {{
        display: flex;
        border-bottom: 1px solid var(--hairline);
    }}
    .money-grid-row .mc-col {{
        flex: 1;
        padding: 11px 16px;
    }}
    .money-grid-row .mc-col:first-child {{
        border-right: 1px solid var(--hairline);
    }}
    .mc-label {{
        font-size: 11px;
        color: #7a7462;
        letter-spacing: 0.3px;
        margin-bottom: 4px;
    }}
    .mc-value {{
        font-family: 'Noto Serif KR', serif;
        font-size: 16px;
        font-weight: 600;
        color: var(--ink);
        font-variant-numeric: tabular-nums;
    }}
    .mc-value .won {{
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 11px;
        font-weight: 400;
        color: #8b8570;
        margin-left: 1px;
    }}
    .mc-diff {{
        margin-top: 3px;
        font-size: 10.5px;
    }}
    .ledger-total-row {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-top: 2px solid var(--gold);
        border-bottom: 2px solid var(--gold);
        background: var(--panel);
        padding: 10px 16px;
    }}
    .ledger-total-row .lt-label {{
        font-size: 12.5px;
        font-weight: 700;
        color: var(--ink);
        letter-spacing: 0.5px;
    }}
    .ledger-total-row .lt-value {{
        font-family: 'Noto Serif KR', serif;
        font-size: 16px;
        font-weight: 700;
        color: var(--ink);
        font-variant-numeric: tabular-nums;
    }}
    .ledger-total-row .lt-value .won {{
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 11px;
        font-weight: 400;
        color: #8b8570;
    }}

    /* ---------- 총 합계 배너 ---------- */
    .grand-total-box {{
        margin-top: 8px;
        background: var(--ink);
        color: #f4efe1;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-left: 4px solid var(--gold);
    }}
    .grand-total-box .gt-label {{
        font-size: 12px;
        letter-spacing: 2px;
        color: #cbb98a;
    }}
    .grand-total-box .gt-value {{
        font-family: 'Noto Serif KR', serif;
        font-size: 26px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }}
    .grand-total-box .gt-value .won {{
        font-size: 14px;
        font-weight: 400;
        color: #cbb98a;
        margin-left: 2px;
    }}

    /* ---------- AI 코멘트 ---------- */
    .ai-comment-section .ai-comment-text {{
        font-size: 13px;
        line-height: 1.85;
        color: var(--ink-soft);
        background: var(--panel);
        border-left: 3px solid var(--gold);
        padding: 14px 18px;
        margin: 0;
        font-family: 'Noto Serif KR', serif;
        font-weight: 500;
    }}

    /* ---------- 푸터 ---------- */
    .report-footer {{
        margin-top: 24px;
        padding-top: 10px;
        border-top: 1px solid var(--hairline);
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #a39d89;
        letter-spacing: 0.5px;
    }}

    @media print {{
        body {{ background: #fff; }}
        .page {{ box-shadow: none; padding: 0 4mm; }}
        .report-section {{ page-break-inside: avoid; }}
    }}
</style>
</head>
<body>
<div class="page">
    <div class="letterhead-bar"></div>
    <div class="report-header">
        <div class="title-block">
            <div class="eyebrow">DAILY OPERATIONS REPORT</div>
            <h1>{hospital_name} 일일보고서</h1>
            <div class="doc-meta">
                <span><b>{date_str}</b> {weekday_str}</span>
                <span>문서번호 <b>{doc_no}</b></span>
                <span>작성자 <b>{writer}</b></span>
            </div>
        </div>
        <div class="approval-box">
            <div class="approval-title">결&nbsp;&nbsp;재</div>
            <div class="approval-cells">
                <div class="approval-cell"><div class="role">담당</div><div class="stamp-space"></div></div>
                <div class="approval-cell"><div class="role">부서장</div><div class="stamp-space"></div></div>
                <div class="approval-cell"><div class="role">원장</div><div class="stamp-space"></div></div>
            </div>
        </div>
    </div>

    <section class="report-section">
        <h2 class="section-title"><span class="marker"></span>외래 인원 현황</h2>
        <div class="stat-strip">{outpatient_stats}</div>
        {mismatch_note}
    </section>

    <section class="report-section">
        <h2 class="section-title"><span class="marker"></span>입원 / 퇴원 현황</h2>
        <div class="stat-strip">{admission_stats}</div>
    </section>

    <section class="report-section">
        <h2 class="section-title"><span class="marker"></span>수술 및 시술 현황</h2>
        <div class="stat-strip">{proc_stats}</div>
        {proc_items_html}
    </section>

    <section class="report-section">
        <h2 class="section-title"><span class="marker"></span>수납금 내역</h2>
        {payment_grid_html}
    </section>

    <section class="report-section">
        <h2 class="section-title"><span class="marker"></span>할인금 내역</h2>
        {discount_grid_html}
        {discount_total_html}
    </section>

    {custom_section_html}

    <div class="grand-total-box">
        <span class="gt-label">총&nbsp;수납액&nbsp;(현금+카드+기타,&nbsp;절사&nbsp;반영)</span>
        <span class="gt-value">{fmt_won(totals['grand_total'])}<span class="won">원</span></span>
    </div>

    {ai_comment_html}

    <div class="report-footer">
        <span>본 보고서는 입력/업로드된 데이터를 기준으로 자동 생성되었습니다.</span>
        <span>생성일시 {generated_at} · 주식회사 메디엄</span>
    </div>
</div>
</body>
</html>
"""
