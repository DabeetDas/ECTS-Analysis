from typing import List, Dict, Any, Optional

METRIC_INSIGHT_DEFINITIONS = [
    {
        "key": "total_income_cr",
        "label": "Total Income",
        "format": "crore",
        "coverage": "fy25",
        "better": "higher",
        "topics": ["Interest Income", "Non Interest Income", "Fee Income", "Treasury Income", "Loan Growth", "Deposit Pricing"],
        "keywords": ["income", "interest income", "fee", "treasury", "loan growth", "business growth"],
        "adjacentMetrics": ["nim_pct", "credit_deposit_pct", "casa_pct"]
    },
    {
        "key": "profit_after_tax_cr",
        "label": "PAT",
        "format": "crore",
        "coverage": "fy25",
        "better": "higher",
        "topics": ["Profit Growth", "Operating Profit", "Net Interest Income", "Provisions", "Treasury Gains", "Asset Quality"],
        "keywords": ["profit", "pat", "nii", "provision", "recovery", "treasury", "operating profit"],
        "adjacentMetrics": ["total_income_cr", "total_expenditure_cr", "nim_pct", "gnpa_pct"]
    },
    {
        "key": "total_expenditure_cr",
        "label": "Total Expenditure",
        "format": "crore",
        "coverage": "fy25",
        "better": "lower",
        "topics": ["Operating Expenses", "Employee Expenses", "Provisions", "Funding Cost", "Technology Spend"],
        "keywords": ["expense", "expenditure", "cost", "employee", "provision", "technology", "funding cost"],
        "adjacentMetrics": ["efficiency_ratio_pct", "nim_pct", "gnpa_pct"]
    },
    {
        "key": "z_score",
        "label": "Bank Z Score",
        "format": "number",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Profitability", "Capital Adequacy", "Asset Quality", "Volatility", "Risk Management"],
        "keywords": ["capital", "asset quality", "risk", "profitability", "stability", "volatility"],
        "adjacentMetrics": ["roa_pct", "crar_pct", "gnpa_pct"]
    },
    {
        "key": "efficiency_ratio_pct",
        "label": "Efficiency Ratio",
        "format": "percent",
        "coverage": "multi-year",
        "better": "lower",
        "topics": ["Operating Expenses", "Operational Efficiency", "Employee Cost", "Branch Network", "Technology Transformation"],
        "keywords": ["efficiency", "operating expense", "employee", "branch", "technology", "cost"],
        "adjacentMetrics": ["total_expenditure_cr", "roa_pct"]
    },
    {
        "key": "roa_pct",
        "label": "ROA",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Return on Assets", "Profitability", "Profit Growth", "Asset Quality"],
        "keywords": ["roa", "return on assets", "profitability", "profit", "assets"],
        "adjacentMetrics": ["profit_after_tax_cr", "z_score"]
    },
    {
        "key": "roe_pct",
        "label": "ROE",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Return on Equity", "Profitability", "Shareholder Returns", "Capital Adequacy"],
        "keywords": ["roe", "return on equity", "shareholder", "profitability", "capital"],
        "adjacentMetrics": ["profit_after_tax_cr", "crar_pct"]
    },
    {
        "key": "nim_pct",
        "label": "NIM",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Net Interest Margin", "Loan Yields", "Deposit Cost", "Funding Cost", "Interest Rate Repricing"],
        "keywords": ["nim", "margin", "yield", "deposit cost", "funding cost", "repricing", "interest rate"],
        "adjacentMetrics": ["total_income_cr", "casa_pct", "credit_deposit_pct"]
    },
    {
        "key": "gnpa_pct",
        "label": "GNPA",
        "format": "percent",
        "coverage": "multi-year",
        "better": "lower",
        "topics": ["Gross NPA", "Asset Quality", "Slippages", "Recoveries", "Provisioning"],
        "keywords": ["gnpa", "npa", "asset quality", "slippage", "recovery", "provision"],
        "adjacentMetrics": ["nnpa_pct", "pcr_pct", "profit_after_tax_cr"]
    },
    {
        "key": "nnpa_pct",
        "label": "NNPA",
        "format": "percent",
        "coverage": "multi-year",
        "better": "lower",
        "topics": ["Net NPA", "Provision Coverage", "Recoveries", "Write-Offs", "Asset Quality"],
        "keywords": ["nnpa", "net npa", "provision", "recovery", "write off", "asset quality"],
        "adjacentMetrics": ["gnpa_pct", "pcr_pct"]
    },
    {
        "key": "casa_pct",
        "label": "CASA",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["CASA", "Deposit Growth", "Liability Franchise", "Deposit Pricing", "Funding Cost"],
        "keywords": ["casa", "deposit", "savings", "current account", "liability", "funding cost"],
        "adjacentMetrics": ["nim_pct", "lcr_pct"]
    },
    {
        "key": "crar_pct",
        "label": "CRAR",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Capital Adequacy", "Risk Weighted Assets", "Capital Raising", "CET1 Ratio", "Loan Growth Capacity"],
        "keywords": ["crar", "capital", "risk weighted", "cet1", "capital adequacy", "rwa"],
        "adjacentMetrics": ["z_score", "cet1_pct"]
    },
    {
        "key": "lcr_pct",
        "label": "LCR",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Liquidity Coverage Ratio", "Liquidity Management", "Deposit Growth", "CASA", "ALM Management"],
        "keywords": ["lcr", "liquidity", "alm", "deposit", "hqlA", "cash outflow"],
        "adjacentMetrics": ["casa_pct", "credit_deposit_pct"]
    },
    {
        "key": "credit_deposit_pct",
        "label": "Credit Deposit",
        "format": "percent",
        "coverage": "multi-year",
        "better": "contextual",
        "topics": ["Credit Deposit Ratio", "Advances Growth", "Deposit Growth", "Loan Growth", "Liquidity Management"],
        "keywords": ["credit deposit", "advances", "deposit growth", "loan growth", "cd ratio"],
        "adjacentMetrics": ["lcr_pct", "casa_pct"]
    },
    {
        "key": "pcr_pct",
        "label": "PCR",
        "format": "percent",
        "coverage": "multi-year",
        "better": "higher",
        "topics": ["Provision Coverage Ratio", "Provisioning", "Asset Quality", "Recoveries", "Write-Offs"],
        "keywords": ["pcr", "provision coverage", "provision", "npa", "recovery"],
        "adjacentMetrics": ["gnpa_pct", "nnpa_pct"]
    }
]

def format_crore(val: str) -> str:
    try:
        fval = float(val)
        return str(int(fval)) if fval.is_integer() else f"{fval:.2f}"
    except (ValueError, TypeError):
        return val

def format_percent(val: str) -> str:
    try:
        fval = float(val)
        return f"{int(fval)}%" if fval.is_integer() else f"{fval:.2f}%"
    except (ValueError, TypeError):
        return val

def loose_match(a: str, b: str) -> bool:
    # A simple inclusion or exact match based on length
    a_norm = " ".join(a.strip().lower().split())
    b_norm = " ".join(b.strip().lower().split())
    return a_norm in b_norm or b_norm in a_norm

def get_metric_definition(metric_key: str) -> Optional[Dict]:
    for metric in METRIC_INSIGHT_DEFINITIONS:
        if metric["key"] == metric_key:
            return metric
    return None

def normalize(val: str) -> str:
    return val.strip().lower()

def is_finite_number(val: Any) -> bool:
    try:
        fval = float(val)
        return fval != float('inf') and fval != float('-inf') and fval == fval
    except (ValueError, TypeError):
        return False

def recency_score(call_date: str) -> float:
    try:
        year = int(str(call_date)[:4])
        return max(0, year - 2020)
    except (ValueError, TypeError):
        return 0

def retrieve_evidence(metric: Dict, observations: List[Dict], topic_hierarchy: Dict) -> List[Dict]:
    direct_topics = set(normalize(t) for t in metric["topics"])
    expanded_topics = set()
    
    for t in metric["topics"]:
        subs = topic_hierarchy.get(t, [])
        for sub in subs:
            expanded_topics.add(normalize(sub))
            
    for key in metric["adjacentMetrics"]:
        mdef = get_metric_definition(key)
        if mdef:
            for t in mdef["topics"]:
                expanded_topics.add(normalize(t))

    keywords = [normalize(k) for k in metric["keywords"]]

    all_evidence = []
    
    for obs in observations:
        topic_name = obs.get("topic_name", "")
        topic_norm = normalize(topic_name)
        excerpts = obs.get("excerpts", [])
        
        text_norm = normalize(f"{topic_name} {' '.join(excerpts)}")
        
        keyword_matches = sum(1 for k in keywords if k in text_norm)
        
        direct_match = any(loose_match(topic_norm, mt) for mt in direct_topics)
        expanded_match = any(loose_match(topic_norm, mt) for mt in expanded_topics)
        
        if not direct_match and not expanded_match and keyword_matches == 0:
            continue
            
        match_type = "direct" if direct_match else ("expanded" if expanded_match else "keyword")
        mention_count = obs.get("mention_count", 0)
        call_date = obs.get("call_date", "")
        
        score = (8 if direct_match else 0) + (4 if expanded_match else 0) + (keyword_matches * 2) + min(mention_count, 8)
                # recency_score(call_date)
                
        for excerpt in excerpts[:3]:
            if not excerpt.strip():
                continue
            all_evidence.append({
                "topic": topic_name,
                "excerpt": excerpt,
                "callDate": call_date,
                "quarter": obs.get("quarter"),
                "score": score,
                "matchType": match_type
            })
            
    # Sort by score descending
    all_evidence.sort(key=lambda x: x["score"], reverse=True)
    return all_evidence[:8]

def format_metric_value(val: float, metric: Dict) -> str:
    if metric["format"] == "crore":
        return format_crore(str(val))
    if metric["format"] == "percent":
        return format_percent(str(val))
    return f"{val:.2f}"

def component_note(row: Dict, key: str, label: str) -> str:
    val = row.get(key)
    if is_finite_number(val):
        return f"{label}: {format_crore(str(val))}."
    return ""

def build_numeric_notes(metric: Dict, financial_rows: List[Dict], current: Dict, previous: Optional[Dict], current_value: float, previous_value: Optional[float]) -> List[str]:
    if metric["coverage"] == "fy25":
        notes = [f"{metric['label']} is available only for {current.get('fiscal_year')} in the uploaded workbook."]
        if metric["key"] == "profit_after_tax_cr":
            notes.append(component_note(current, "total_income_cr", "Total Income"))
            notes.append(component_note(current, "total_expenditure_cr", "Total Expenditure"))
        if metric["key"] == "total_expenditure_cr":
            notes.append(component_note(current, "interest_expended_cr", "Interest Expended"))
            notes.append(component_note(current, "operating_expenses_cr", "Operating Expenses"))
            notes.append(component_note(current, "provisions_contingencies_cr", "Provisions and Contingencies"))
            
        return [n for n in notes if n]

    if previous is None or previous_value is None:
        return [f"{metric['label']} has no prior-year value available for comparison."]

    direction = "increased" if current_value > previous_value else ("declined" if current_value < previous_value else "was flat")
    
    rows_with_metric = [row for row in financial_rows if is_finite_number(row.get(metric["key"]))]
    history_string = ", ".join(f"{r.get('fiscal_year')}: {format_metric_value(float(r[metric['key']]), metric)}" for r in rows_with_metric)

    return [
        f"{metric['label']} {direction} from {format_metric_value(previous_value, metric)} in {previous.get('fiscal_year')} to {format_metric_value(current_value, metric)} in {current.get('fiscal_year')}.",
        f"Historical timeline: {history_string}"
    ]

def build_local_takeaway(metric: Dict, current: Dict, current_value: float, previous: Optional[Dict], previous_value: Optional[float], evidence_strength: str) -> str:
    evidence_phrase = (
        "Direct transcript evidence was found for this metric." if evidence_strength == "direct"
        else "Direct transcript evidence was limited, so adjacent topics were used." if evidence_strength == "expanded"
        else "No direct transcript evidence was found; use the numeric decomposition as the primary explanation."
    )

    if metric["coverage"] == "fy25" or previous is None or previous_value is None:
        return f"{metric['label']} is {format_metric_value(current_value, metric)} in {current.get('fiscal_year')}. YoY movement is not available from the uploaded workbook. {evidence_phrase}"

    direction = "up" if current_value > previous_value else ("down" if current_value < previous_value else "flat")
    return f"{metric['label']} moved {direction} from {previous.get('fiscal_year')} to {current.get('fiscal_year')}. {evidence_phrase}"

def build_metric_insight(metric_key: str, financial_rows: List[Dict], observations: List[Dict], topic_hierarchy: Dict) -> Optional[Dict]:
    metric = get_metric_definition(metric_key)
    if not metric:
        return None

    rows_with_metric = [row for row in financial_rows if is_finite_number(row.get(metric["key"]))]
    if not rows_with_metric:
        return None
        
    current = rows_with_metric[-1]
    previous = rows_with_metric[-2] if len(rows_with_metric) >= 2 and metric["coverage"] == "multi-year" else None
    
    current_value = float(current[metric["key"]])
    previous_value = float(previous[metric["key"]]) if previous and metric["key"] in previous else None
    
    evidence = retrieve_evidence(metric, observations, topic_hierarchy)

    
    evidence_strength = "direct" if any(e["matchType"] == "direct" for e in evidence) \
                        else "expanded" if evidence \
                        else "weak"
                        
    movement = current_value - previous_value if previous_value is not None else None
    direction = "up" if movement is not None and movement > 0 else ("down" if movement is not None and movement < 0 else "flat") if movement is not None else None
    
    percent_change = f"{(movement / abs(previous_value)) * 100:.2f}%" if movement is not None and previous_value and previous_value != 0 else None
    
    numeric_notes = build_numeric_notes(metric, financial_rows, current, previous, current_value, previous_value)
    local_takeaway = build_local_takeaway(metric, current, current_value, previous, previous_value, evidence_strength)
    
    return {
        "metric": metric,
        "currentYear": current.get("fiscal_year", ""),
        "currentValue": format_metric_value(current_value, metric),
        "previousYear": previous.get("fiscal_year") if previous else None,
        "previousValue": format_metric_value(previous_value, metric) if previous_value is not None else None,
        "absoluteChange": format_metric_value(movement, metric) if movement is not None else None,
        "percentChange": percent_change,
        "direction": direction,
        "evidence": evidence,
        "evidenceStrength": evidence_strength,
        "localTakeaway": local_takeaway,
        "numericNotes": numeric_notes
    }

# Example Testing Usage
if __name__ == "__main__":
    import json
    # You can read from outputs/psb_corpus_analysis.json here
    print("Run `build_metric_insight(metric_key, rows, obs, hierarchy)` to debug.")
