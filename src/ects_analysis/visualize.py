from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


BANK_LABELS = {
    "BOB": "Bank of Baroda",
    "SBI": "State Bank of India",
    "PNB": "Punjab National Bank",
}

BANK_BRANDS = {
    "BOB": {
        "primary": "#C27D38",
        "secondary": "#0F1E36",
        "accent": "#F5F0E6",
    },
    "SBI": {
        "primary": "#1E6B7B",
        "secondary": "#0F1E36",
        "accent": "#F5F0E6",
    },
    "PNB": {
        "primary": "#8A6A3F",
        "secondary": "#0F1E36",
        "accent": "#F5F0E6",
    },
}


def load_corpus_analysis(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Corpus analysis JSON must be an object")

    required_keys = ["trend_analysis", "competitor_analysis", "observations"]
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Corpus analysis JSON is missing: {', '.join(missing)}")
    if not isinstance(payload.get("competitor_analysis"), dict):
        raise ValueError("Corpus analysis `competitor_analysis` must be an object")
    return payload


def load_financial_analysis(path: Path) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Financial CSV not found: {path}")

    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        return {}

    required_fields = {"bank", "fiscal_year"}
    missing_fields = required_fields - set(rows[0])
    if missing_fields:
        raise ValueError(f"Financial CSV is missing: {', '.join(sorted(missing_fields))}")

    by_bank: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        bank = str(row.get("bank", "")).strip()
        if not bank:
            continue
        normalized = {str(key): str(value or "").strip() for key, value in row.items() if key is not None}
        by_bank[bank].append(normalized)

    return {
        bank: sorted(bank_rows, key=lambda item: fiscal_year_sort_key(item.get("fiscal_year", "")))
        for bank, bank_rows in by_bank.items()
    }


def load_topic_hierarchy(path: Path) -> dict[str, list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Topic hierarchy JSON must be an object")

    hierarchy: dict[str, list[str]] = {}
    for topic, subtopics in payload.items():
        if not isinstance(topic, str) or not isinstance(subtopics, list):
            raise ValueError("Topic hierarchy must map topic names to subtopic lists")
        if not all(isinstance(subtopic, str) for subtopic in subtopics):
            raise ValueError("Topic hierarchy subtopic lists must contain only strings")
        hierarchy[topic] = subtopics
    return hierarchy


def export_dashboard_payload(
    analysis: dict[str, Any],
    *,
    financial_analysis: dict[str, list[dict[str, str]]] | None = None,
    topic_hierarchy: dict[str, list[str]] | None = None,
    profile_bank: str = "BOB",
) -> dict[str, Any]:
    companies = sorted(
        {
            *[
                str(document.get("company"))
                for document in _list(analysis.get("documents"))
                if isinstance(document, dict) and document.get("company")
            ],
            *[
                str(observation.get("company"))
                for observation in _list(analysis.get("observations"))
                if isinstance(observation, dict) and observation.get("company")
            ],
        },
        key=bank_sort_key,
    )

    return {
        "metadata": {
            "title": "PSB Earnings Call Intelligence",
            "profile_bank": profile_bank,
            "generated_from": "ects_analysis.visualize",
        },
        "banks": {
            company: {
                "code": company,
                "label": BANK_LABELS.get(company, company),
                "brand": BANK_BRANDS.get(
                    company,
                    {"primary": "#5C6773", "secondary": "#0F1E36", "accent": "#F5F0E6"},
                ),
            }
            for company in companies
        },
        "topic_hierarchy": topic_hierarchy or {},
        "financial_analysis": financial_analysis or {},
        "analysis": analysis,
    }


def write_dashboard_payload(
    *,
    input_path: Path,
    output_path: Path,
    financials_path: Path | None,
    topic_hierarchy_path: Path | None,
    profile_bank: str,
) -> None:
    analysis = load_corpus_analysis(input_path)
    financial_analysis = load_financial_analysis(financials_path) if financials_path else {}
    topic_hierarchy = load_topic_hierarchy(topic_hierarchy_path) if topic_hierarchy_path else {}
    payload = export_dashboard_payload(
        analysis,
        financial_analysis=financial_analysis,
        topic_hierarchy=topic_hierarchy,
        profile_bank=profile_bank,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fiscal_year_sort_key(value: str) -> tuple[int, str]:
    digits = "".join(character for character in str(value) if character.isdigit())
    return (int(digits) if digits else 0, str(value))


def bank_sort_key(value: str) -> tuple[str, str]:
    code = str(value)
    return (BANK_LABELS.get(code, code).casefold(), code.casefold())


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def main() -> None:
    parser = argparse.ArgumentParser(description="Export dashboard data for the Next.js frontend.")
    parser.add_argument("--input", default="outputs/psb_corpus_analysis.json", help="Corpus analysis JSON")
    parser.add_argument(
        "--output",
        default="frontend/public/data/dashboard-data.json",
        help="Output JSON consumed by the frontend",
    )
    parser.add_argument(
        "--financials",
        default="data/psb_financials_dummy.csv",
        help="Financial CSV to overlay in the frontend",
    )
    parser.add_argument(
        "--topic-hierarchy",
        default="data/psb_seed_topics.json",
        help="Topic/subtopic hierarchy JSON",
    )
    parser.add_argument("--profile-bank", default="BOB", help="Featured bank code")
    parser.add_argument(
        "--view",
        choices=["corpus"],
        default="corpus",
        help="Kept for CLI compatibility; the React frontend renders the view.",
    )
    args = parser.parse_args()

    write_dashboard_payload(
        input_path=Path(args.input),
        output_path=Path(args.output),
        financials_path=Path(args.financials) if args.financials else None,
        topic_hierarchy_path=Path(args.topic_hierarchy) if args.topic_hierarchy else None,
        profile_bank=args.profile_bank,
    )
    print(f"Wrote frontend dashboard data to {args.output}")


if __name__ == "__main__":
    main()
