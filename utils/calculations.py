"""모든 합계/증감 계산은 이 모듈에서 결정론적으로 처리합니다.

중요: 금액 계산에는 절대 AI(LLM)를 사용하지 않습니다.
Gemini는 report_generator에서 '코멘트 문장' 생성에만 관여하며,
표에 들어가는 숫자는 100% 이 모듈에서 계산된 값을 그대로 사용합니다.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


def to_decimal(value: Any) -> Decimal:
    """입력값(str/int/float/Decimal, 콤마 포함 가능)을 Decimal로 안전 변환."""
    if isinstance(value, Decimal):
        return value
    if value in (None, ""):
        return Decimal("0")
    try:
        cleaned = str(value).replace(",", "").replace("원", "").strip()
        if cleaned == "":
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def fmt_won(value: Decimal) -> str:
    """1,234,000원 형태로 포맷."""
    value = to_decimal(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}{int(value):,}"


def outpatient_breakdown_sum(outpatient: Dict[str, int]) -> int:
    return (
        outpatient.get("first_visit", 0)
        + outpatient.get("new_patient", 0)
        + outpatient.get("revisit", 0)
        + outpatient.get("unclassified", 0)
    )


def custom_items_sum(custom_items: list, category: str) -> Decimal:
    total = Decimal("0")
    for item in custom_items:
        if item.get("category") == category:
            total += to_decimal(item.get("amount", 0))
    return total


def compute_totals(report_data: Dict[str, Any]) -> Dict[str, Any]:
    payment = report_data["payment"]
    discount = report_data["discount"]
    custom_amounts = custom_items_sum(report_data.get("custom_items", []), "금액")

    cash = to_decimal(payment["cash"])
    card = to_decimal(payment["card"])
    unpaid = to_decimal(payment["unpaid"])
    non_covered = to_decimal(payment["non_covered"])
    rounding_cut = to_decimal(payment["rounding_cut"])

    exemption = to_decimal(discount["exemption"])
    disc = to_decimal(discount["discount"])

    total_received = cash + card + custom_amounts  # 실제 수납액(현금+카드+커스텀 금액 항목)
    total_discount = exemption + disc

    outpatient = report_data["outpatient"]
    breakdown_sum = outpatient_breakdown_sum(outpatient)
    outpatient_mismatch = breakdown_sum != outpatient.get("total", 0)

    admission = report_data["admission"]
    net_admission_change = admission.get("admitted_today", 0) - admission.get(
        "discharged_today", 0
    )

    return {
        "cash": cash,
        "card": card,
        "unpaid": unpaid,
        "non_covered": non_covered,
        "rounding_cut": rounding_cut,
        "exemption": exemption,
        "discount": disc,
        "custom_amount_sum": custom_amounts,
        "total_received": total_received,
        "total_discount": total_discount,
        "grand_total": total_received - rounding_cut,  # 절사 반영 최종 합계
        "outpatient_breakdown_sum": breakdown_sum,
        "outpatient_mismatch": outpatient_mismatch,
        "net_admission_change": net_admission_change,
    }


def compute_diff(current: Optional[Decimal], previous: Optional[Decimal]):
    """전일 대비 증감(값, 증감률%) 반환. previous가 없으면 None."""
    if previous is None:
        return None, None
    current = to_decimal(current)
    previous = to_decimal(previous)
    diff = current - previous
    if previous == 0:
        pct = None
    else:
        pct = float(diff / previous * 100)
    return diff, pct
