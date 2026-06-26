from __future__ import annotations

from typing import Any

from pipeline_backend.schemas import ExtractedFinancials, MetricValue, SourceRef
from pipeline_backend.tools.financial_schema import METRIC_SPECS, all_aliases, normalize_label


ALIASES = all_aliases()


def normalize_extracted_payload(payload: dict[str, Any]) -> ExtractedFinancials:
    bank_name = _string(payload.get("bank_name") or payload.get("bank") or payload.get("company"))
    raw_metrics = _collect_raw_metrics(payload)
    metrics: list[MetricValue] = []
    warnings: list[str] = []

    for raw in raw_metrics:
        metric_key = resolve_metric_key(raw.get("metric") or raw.get("label") or raw.get("metric_key"))
        if not metric_key:
            warnings.append(f"Unmapped metric: {raw.get('metric') or raw.get('label') or raw.get('metric_key')}")
            continue
        spec = METRIC_SPECS[metric_key]
        for period, value in _period_values(raw).items():
            number = parse_number(value)
            if number is None:
                warnings.append(f"Invalid value for {spec.label} {period}: {value}")
                continue
            normalized_value = normalize_unit(number, spec.unit)
            metrics.append(
                MetricValue(
                    metric_key=metric_key,
                    label=spec.label,
                    period=normalize_period(period),
                    value=normalized_value,
                    unit=spec.unit,  # type: ignore[arg-type]
                    source=_source_ref(raw),
                    confidence=float(raw.get("confidence") or 0.75),
                )
            )

    periods = sorted({metric.period for metric in metrics}, key=period_sort_key)
    warnings.extend(validate_metric_coverage(metrics))
    return ExtractedFinancials(
        bank_name=bank_name,
        periods=periods,
        metrics=sorted(metrics, key=lambda item: (item.metric_key, period_sort_key(item.period))),
        warnings=warnings,
        raw_payload=payload,
    )


def resolve_metric_key(label: Any) -> str | None:
    if label is None:
        return None
    normalized = normalize_label(str(label))
    if normalized in ALIASES:
        return ALIASES[normalized]
    for alias, key in ALIASES.items():
        if alias and (alias in normalized or normalized in alias):
            return key
    return None


def normalize_unit(value: float, unit: str) -> float:
    if unit == "crore":
        return round(value / 10_000_000, 2) if abs(value) >= 10_000_000 else round(value, 2)
    if unit == "percent":
        return round(value * 100, 2) if abs(value) <= 2 else round(value, 2)
    return round(value, 4)


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    text = text.replace("₹", "").replace("Rs.", "").replace("INR", "")
    multiplier = 1.0
    lower = text.lower()
    if "lakh crore" in lower:
        multiplier = 100000
    elif "crore" in lower or "cr" in lower:
        multiplier = 1
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def normalize_period(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("FY"):
        return text.replace(" ", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4 and digits.startswith("20"):
        return f"FY{digits[-2:]}"
    if len(digits) == 2:
        return f"FY{digits}"
    return text or "UNKNOWN"


def period_sort_key(value: str) -> tuple[int, str]:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return (int(digits) if digits else 0, str(value))


def validate_metric_coverage(metrics: list[MetricValue]) -> list[str]:
    warnings: list[str] = []
    by_metric: dict[str, set[str]] = {}
    for metric in metrics:
        by_metric.setdefault(metric.metric_key, set()).add(metric.period)
    for metric_key in ("total_income_cr", "profit_after_tax_cr", "total_expenditure_cr"):
        periods = by_metric.get(metric_key, set())
        if periods and periods != {"FY25"}:
            warnings.append(f"{metric_key} is usually FY25-only in data_new.xlsx but extracted periods are {sorted(periods)}")
    return warnings


def _collect_raw_metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("metrics"), list):
        return [item for item in payload["metrics"] if isinstance(item, dict)]
    if isinstance(payload.get("financials"), dict):
        rows: list[dict[str, Any]] = []
        for metric, values in payload["financials"].items():
            if isinstance(values, dict):
                rows.append({"metric": metric, "values": values})
            else:
                rows.append({"metric": metric, "period": payload.get("period") or "FY25", "value": values})
        return rows
    return []


def _period_values(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("values"), dict):
        return row["values"]
    if isinstance(row.get("period_values"), dict):
        return row["period_values"]
    period = row.get("period") or row.get("year") or row.get("fiscal_year") or "FY25"
    return {str(period): row.get("value")}


def _source_ref(row: dict[str, Any]) -> SourceRef | None:
    source = row.get("source") if isinstance(row.get("source"), dict) else row
    text = source.get("source_text") or source.get("text") or source.get("excerpt")
    if not any(key in source for key in ("page", "slide", "chunk_id")) and not text:
        return None
    return SourceRef(
        document_type="presentation",
        page=_optional_int(source.get("page") or source.get("source_page")),
        slide=_optional_int(source.get("slide") or source.get("source_slide")),
        chunk_id=_string(source.get("chunk_id")),
        text=_string(text),
    )


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _string(value: Any) -> str | None:
    return str(value).strip() if value is not None and str(value).strip() else None

