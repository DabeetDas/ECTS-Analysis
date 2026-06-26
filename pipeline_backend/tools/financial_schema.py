from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    unit: str
    coverage: str
    aliases: tuple[str, ...]
    topics: tuple[str, ...]
    keywords: tuple[str, ...]
    adjacent_metrics: tuple[str, ...] = ()


METRIC_SPECS: dict[str, MetricSpec] = {
    "total_income_cr": MetricSpec(
        "total_income_cr",
        "Total Income",
        "crore",
        "fy25",
        ("total income", "income total", "total revenue"),
        ("Interest Income", "Non Interest Income", "Fee Income", "Treasury Income", "Loan Growth"),
        ("income", "interest income", "fee", "treasury", "revenue"),
        ("nim_pct", "credit_deposit_pct"),
    ),
    "interest_income_cr": MetricSpec(
        "interest_income_cr",
        "Interest Income",
        "crore",
        "fy25",
        ("interest income", "interest earned", "interest"),
        ("Interest Income", "Loan Yields", "Advances Growth"),
        ("interest income", "interest earned", "yield"),
    ),
    "other_income_cr": MetricSpec(
        "other_income_cr",
        "Other Income",
        "crore",
        "fy25",
        ("other income", "non interest income", "fee income"),
        ("Non Interest Income", "Fee Income", "Treasury Income"),
        ("other income", "fee", "treasury", "commission"),
    ),
    "total_expenditure_cr": MetricSpec(
        "total_expenditure_cr",
        "Total Expenditure",
        "crore",
        "fy25",
        ("total expenditure", "total expenses", "expenditure total"),
        ("Operating Expenses", "Employee Expenses", "Provisions", "Funding Cost"),
        ("expense", "expenditure", "cost", "employee", "provision"),
        ("efficiency_ratio_pct", "gnpa_pct"),
    ),
    "interest_expended_cr": MetricSpec(
        "interest_expended_cr",
        "Interest Expended",
        "crore",
        "fy25",
        ("interest expended", "interest expense", "interest paid"),
        ("Funding Cost", "Deposit Cost", "Interest Rates"),
        ("interest expense", "interest expended", "funding cost", "deposit cost"),
    ),
    "operating_expenses_cr": MetricSpec(
        "operating_expenses_cr",
        "Operating Expenses",
        "crore",
        "fy25",
        ("operating expenses", "opex", "operating expense"),
        ("Operating Expenses", "Employee Expenses", "Operational Efficiency"),
        ("operating expense", "opex", "employee", "branch", "technology"),
    ),
    "provisions_contingencies_cr": MetricSpec(
        "provisions_contingencies_cr",
        "Provisions and Contingencies",
        "crore",
        "fy25",
        ("provisions and contingencies", "provisions", "provisioning"),
        ("Provisioning", "Asset Quality", "Credit Cost", "Recoveries"),
        ("provision", "credit cost", "npa", "recovery"),
    ),
    "profit_after_tax_cr": MetricSpec(
        "profit_after_tax_cr",
        "PAT",
        "crore",
        "fy25",
        ("pat", "profit after tax", "net profit", "profit"),
        ("Profit Growth", "Operating Profit", "Net Interest Income", "Provisions", "Treasury Gains"),
        ("profit", "pat", "nii", "provision", "treasury", "operating profit"),
        ("total_income_cr", "total_expenditure_cr", "nim_pct", "gnpa_pct"),
    ),
    "nim_pct": MetricSpec(
        "nim_pct",
        "NIM",
        "percent",
        "multi-year",
        ("nim", "net interest margin"),
        ("Net Interest Margin", "Loan Yields", "Deposit Cost", "Funding Cost", "Interest Rate Repricing"),
        ("nim", "margin", "yield", "deposit cost", "funding cost", "repricing"),
    ),
    "roa_pct": MetricSpec(
        "roa_pct",
        "ROA",
        "percent",
        "multi-year",
        ("roa", "return on assets", "return on assets ratio"),
        ("Return on Assets", "Profitability", "Profit Growth", "Asset Quality"),
        ("roa", "return on assets", "profitability", "profit"),
    ),
    "roe_pct": MetricSpec(
        "roe_pct",
        "ROE",
        "percent",
        "multi-year",
        ("roe", "return on equity", "return on equity ratio"),
        ("Return on Equity", "Profitability", "Shareholder Returns", "Capital Adequacy"),
        ("roe", "return on equity", "shareholder", "capital"),
    ),
    "efficiency_ratio_pct": MetricSpec(
        "efficiency_ratio_pct",
        "Efficiency Ratio",
        "percent",
        "multi-year",
        ("efficiency ratio", "cost to income ratio", "cost income ratio"),
        ("Operating Expenses", "Operational Efficiency", "Employee Cost", "Branch Network"),
        ("efficiency", "operating expense", "employee", "branch", "technology", "cost"),
    ),
    "gnpa_pct": MetricSpec(
        "gnpa_pct",
        "GNPA",
        "percent",
        "multi-year",
        ("gnpa", "gross npa", "gross non performing assets"),
        ("Gross NPA", "Asset Quality", "Slippages", "Recoveries", "Provisioning"),
        ("gnpa", "npa", "asset quality", "slippage", "recovery", "provision"),
    ),
    "nnpa_pct": MetricSpec(
        "nnpa_pct",
        "NNPA",
        "percent",
        "multi-year",
        ("nnpa", "net npa", "net non performing assets"),
        ("Net NPA", "Provision Coverage", "Recoveries", "Write-Offs", "Asset Quality"),
        ("nnpa", "net npa", "provision", "recovery", "write off", "asset quality"),
    ),
    "casa_pct": MetricSpec(
        "casa_pct",
        "CASA",
        "percent",
        "multi-year",
        ("casa", "casa ratio"),
        ("CASA", "Deposit Growth", "Liability Franchise", "Deposit Pricing", "Funding Cost"),
        ("casa", "deposit", "savings", "current account", "liability"),
    ),
    "crar_pct": MetricSpec(
        "crar_pct",
        "CRAR",
        "percent",
        "multi-year",
        ("crar", "capital adequacy ratio", "capital to risk weight assets ratio"),
        ("Capital Adequacy", "Risk Weighted Assets", "Capital Raising", "CET1 Ratio"),
        ("crar", "capital", "risk weighted", "cet1", "rwa"),
    ),
    "lcr_pct": MetricSpec(
        "lcr_pct",
        "LCR",
        "percent",
        "multi-year",
        ("lcr", "liquidity coverage ratio"),
        ("Liquidity Coverage Ratio", "Liquidity Management", "Deposit Growth", "CASA", "ALM Management"),
        ("lcr", "liquidity", "alm", "deposit", "hqlA", "cash outflow"),
    ),
    "z_score": MetricSpec(
        "z_score",
        "Bank Z Score",
        "number",
        "multi-year",
        ("z-score", "z score", "bank z score"),
        ("Profitability", "Capital Adequacy", "Asset Quality", "Volatility", "Risk Management"),
        ("capital", "asset quality", "risk", "profitability", "stability", "volatility"),
    ),
}


def all_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for key, spec in METRIC_SPECS.items():
        aliases[normalize_label(spec.label)] = key
        aliases[normalize_label(key)] = key
        for alias in spec.aliases:
            aliases[normalize_label(alias)] = key
    return aliases


def normalize_label(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())

