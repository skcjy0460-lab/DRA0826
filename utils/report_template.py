"""A4 인쇄에 최적화된 고급풍 HTML 일일보고서 템플릿.

- @page 규칙으로 A4 여백 고정, page-break 제어로 표/카드가 페이지 경계에서 잘리지 않도록 처리
- 네이비 + 골드 톤의 절제된 고급 디자인 (메디엄 브랜드 톤과 통일)
- 인쇄(Ctrl+P) 시 그대로 PDF로 저장 가능하도록 화면용 UI 요소(버튼 등)는 없음
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .calculations import compute_diff, fmt_won, outpatient_breakdown_sum

WEEKDAY_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _diff_badge(diff: Optional[Decimal], pct: Optional[float], unit: str = "원") -> str:
    if diff is None:
        return '<span class="badge badge-neutral">전일 데이터 없음</span>'
    diff = Decimal(diff)
    if diff > 0:
        cls, arrow = "badge-up", "▲"
    elif diff < 0:
        cls, arrow = "badge-down", "▼"
    else:
        cls, arrow = "badge-neutral", "-"
    diff_str = fmt_won(abs(diff)) if unit == "원" else f"{abs(int(diff)):,}"
    pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
    return f'<span class="badge {cls}">{arrow} {diff_str}{unit}{pct_str}</span>'


def _count_row(label: str, value: int) -> str:
    return f"""
    <div class="count-cell">
        <div class="count-label">{label}</div>
        <div class="count-value">{value:,}</div>
    </div>
    """


def _money_row(label: str, value: Decimal, highlight: bool = False, diff_badge: str = "") -> str:
    cls = "money-row highlight" if highlight else "money-row"
    return f"""
    <tr class="{cls}">
        <td class="money-label">{label}</td>
        <td class="money-value">{fmt_won(value)}원</td>
        <td class="money-diff">{diff_badge}</td>
    </tr>
    """


def build_report_html(
    report_data: Dict[str, Any],
    totals: Dict[str, Any],
    prev_totals: Optional[Dict[str, Any]] = None,
    ai_comment: str = "",
) -> str:
    meta = report_data["meta"]
    outpatient = report_data["outpatient"]
    admission = report_data["admission"]
    custom_items = report_data.get("custom_items", [])

    report_date = meta.get("report_date")
    if isinstance(report_date, str):
        date_str = report_date
        weekday_str = ""
    else:
        date_str = report_date.strftime("%Y년 %m월 %d일")
        weekday_str = WEEKDAY_KR[report_date.weekday()]

    hospital_name = meta.get("hospital_name") or "OO병원"
    writer = meta.get("writer") or ""

    # 인원 카운트 카드
    outpatient_cards = "".join(
        [
            _count_row("외래 TOTAL", outpatient.get("total", 0)),
            _count_row("신환", outpatient.get("new_patient", 0)),
            _count_row("초진", outpatient.get("first_visit", 0)),
            _count_row("재진", outpatient.get("revisit", 0)),
            _count_row("미산정", outpatient.get("unclassified", 0)),
            _count_row("순수재원환자", outpatient.get("pure_census", 0)),
        ]
    )

    admission_cards = "".join(
        [
            _count_row("당일 입원", admission.get("admitted_today", 0)),
            _count_row("당일 퇴원", admission.get("discharged_today", 0)),
            _count_row("현재 재원환자수", admission.get("current_census", 0)),
        ]
    )

    breakdown_sum = outpatient_breakdown_sum(outpatient)
    mismatch_note = ""
    if breakdown_sum != outpatient.get("total", 0):
        mismatch_note = (
            f'<div class="note-warning">※ 세부 항목 합계({breakdown_sum:,}명)와 '
            f'외래 TOTAL({outpatient.get("total", 0):,}명)이 일치하지 않습니다. 입력값을 확인해주세요.</div>'
        )

    # 전일 대비 배지
    def diff_for(key_path: str, unit="원") -> str:
        if prev_totals is None:
            return ""
        diff, pct = compute_diff(totals.get(key_path), prev_totals.get(key_path))
        return _diff_badge(diff, pct, unit=unit)

    payment_rows = "".join(
        [
            _money_row("현금", totals["cash"], diff_badge=diff_for("cash")),
            _money_row("카드", totals["card"], diff_badge=diff_for("card")),
            _money_row("미수금", totals["unpaid"], diff_badge=diff_for("unpaid")),
            _money_row("비급여 (참고)", totals["non_covered"]),
            _money_row("절사", totals["rounding_cut"]),
        ]
    )
    if totals["custom_amount_sum"] > 0:
        payment_rows += _money_row("기타 항목 합계", totals["custom_amount_sum"])

    discount_rows = "".join(
        [
            _money_row("감면", totals["exemption"]),
            _money_row("할인", totals["discount"]),
            _money_row("할인 합계", totals["total_discount"], highlight=True),
        ]
    )

    custom_count_items = [c for c in custom_items if c.get("category") == "인원"]
    custom_amount_items = [c for c in custom_items if c.get("category") == "금액"]

    custom_section_html = ""
    if custom_count_items or custom_amount_items:
        rows = ""
        for item in custom_count_items:
            rows += _count_row(item.get("label", ""), int(item.get("amount", 0) or 0))
        custom_people_html = (
            f'<div class="count-grid">{rows}</div>' if custom_count_items else ""
        )
        amount_rows = "".join(
            _money_row(item.get("label", ""), Decimal(str(item.get("amount", 0) or 0)))
            for item in custom_amount_items
        )
        custom_amount_html = (
            f'<table class="money-table"><tbody>{amount_rows}</tbody></table>'
            if custom_amount_items
            else ""
        )
        custom_section_html = f"""
        <section class="report-section">
            <h2 class="section-title">기타 항목</h2>
            {custom_people_html}
            {custom_amount_html}
        </section>
        """

    ai_comment_html = ""
    if ai_comment:
        ai_comment_html = f"""
        <section class="report-section ai-comment-section">
            <h2 class="section-title">경영 브리핑 코멘트</h2>
            <p class="ai-comment-text">{ai_comment}</p>
        </section>
        """

    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{hospital_name} 일일보고서 {date_str}</title>
<style>
    @page {{
        size: A4;
        margin: 14mm 16mm;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        color: #1c2431;
        margin: 0;
        background: #ffffff;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}
    .page {{
        max-width: 780px;
        margin: 0 auto;
        padding: 6mm 2mm;
    }}
    .report-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 3px solid #1a2744;
        padding-bottom: 14px;
        margin-bottom: 20px;
    }}
    .report-header .title-block h1 {{
        font-size: 24px;
        letter-spacing: 1px;
        margin: 0 0 4px 0;
        color: #1a2744;
    }}
    .report-header .title-block .subtitle {{
        font-size: 13px;
        color: #8a6d1f;
        letter-spacing: 3px;
        font-weight: 600;
    }}
    .report-header .meta-block {{
        text-align: right;
        font-size: 13px;
        color: #4a5568;
        line-height: 1.6;
    }}
    .report-section {{
        margin-bottom: 22px;
        page-break-inside: avoid;
    }}
    .section-title {{
        font-size: 15px;
        font-weight: 700;
        color: #ffffff;
        background: #1a2744;
        padding: 7px 14px;
        margin: 0 0 10px 0;
        border-left: 4px solid #c8a24a;
        letter-spacing: 1px;
    }}
    .count-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
    }}
    .count-cell {{
        border: 1px solid #dfe3ea;
        border-radius: 4px;
        padding: 10px 8px;
        text-align: center;
        background: #f7f8fa;
    }}
    .count-label {{
        font-size: 11.5px;
        color: #5b6472;
        margin-bottom: 4px;
    }}
    .count-value {{
        font-size: 19px;
        font-weight: 700;
        color: #1a2744;
    }}
    .note-warning {{
        margin-top: 8px;
        font-size: 11.5px;
        color: #a33;
        background: #fdf2f2;
        border: 1px solid #f3c9c9;
        padding: 6px 10px;
        border-radius: 4px;
    }}
    table.money-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    table.money-table tr {{
        border-bottom: 1px solid #e7e9ee;
    }}
    table.money-table td {{
        padding: 8px 10px;
    }}
    .money-label {{
        color: #3d4654;
        width: 40%;
    }}
    .money-value {{
        text-align: right;
        font-weight: 600;
        width: 30%;
        color: #1a2744;
        font-variant-numeric: tabular-nums;
    }}
    .money-diff {{
        text-align: right;
        width: 30%;
        font-size: 11px;
    }}
    .money-row.highlight td {{
        background: #fbf5e6;
        font-weight: 700;
        border-top: 2px solid #c8a24a;
        border-bottom: 2px solid #c8a24a;
    }}
    .badge {{
        display: inline-block;
        padding: 2px 7px;
        border-radius: 10px;
        font-size: 10.5px;
        font-weight: 600;
    }}
    .badge-up {{ background: #fdeceb; color: #c0392b; }}
    .badge-down {{ background: #eaf3ff; color: #1f5aa6; }}
    .badge-neutral {{ background: #eef0f3; color: #6b7280; }}
    .grand-total-box {{
        margin-top: 10px;
        background: #1a2744;
        color: #ffffff;
        border-radius: 6px;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .grand-total-box .gt-label {{
        font-size: 14px;
        letter-spacing: 2px;
        color: #d8c078;
    }}
    .grand-total-box .gt-value {{
        font-size: 26px;
        font-weight: 800;
    }}
    .ai-comment-section .ai-comment-text {{
        font-size: 13px;
        line-height: 1.8;
        color: #2f3846;
        background: #f7f8fa;
        border-left: 3px solid #c8a24a;
        padding: 14px 16px;
        margin: 0;
    }}
    .report-footer {{
        margin-top: 26px;
        padding-top: 10px;
        border-top: 1px solid #dfe3ea;
        display: flex;
        justify-content: space-between;
        font-size: 10.5px;
        color: #9aa1ab;
    }}
    @media print {{
        .report-section {{ page-break-inside: avoid; }}
        body {{ -webkit-print-color-adjust: exact; }}
    }}
</style>
</head>
<body>
<div class="page">
    <div class="report-header">
        <div class="title-block">
            <h1>{hospital_name} 일일보고서</h1>
            <div class="subtitle">DAILY OPERATIONS REPORT</div>
        </div>
        <div class="meta-block">
            <div>{date_str} {weekday_str}</div>
            <div>작성자: {writer or "-"}</div>
        </div>
    </div>

    <section class="report-section">
        <h2 class="section-title">외래 인원 현황</h2>
        <div class="count-grid">{outpatient_cards}</div>
        {mismatch_note}
    </section>

    <section class="report-section">
        <h2 class="section-title">입원 / 퇴원 현황</h2>
        <div class="count-grid">{admission_cards}</div>
    </section>

    <section class="report-section">
        <h2 class="section-title">수납금 내역</h2>
        <table class="money-table"><tbody>{payment_rows}</tbody></table>
    </section>

    <section class="report-section">
        <h2 class="section-title">할인금 내역</h2>
        <table class="money-table"><tbody>{discount_rows}</tbody></table>
    </section>

    {custom_section_html}

    <div class="grand-total-box">
        <span class="gt-label">총 수납액 (현금+카드+기타, 절사 반영)</span>
        <span class="gt-value">{fmt_won(totals['grand_total'])}원</span>
    </div>

    {ai_comment_html}

    <div class="report-footer">
        <span>본 보고서는 입력/업로드된 데이터를 기준으로 자동 생성되었습니다.</span>
        <span>생성일시: {generated_at} · 주식회사 메디엄</span>
    </div>
</div>
</body>
</html>
"""
