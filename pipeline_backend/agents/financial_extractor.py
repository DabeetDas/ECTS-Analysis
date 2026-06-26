from __future__ import annotations

from pathlib import Path

from pipeline_backend.schemas import ExtractedFinancials
from pipeline_backend.tools.financial_normalizer import normalize_extracted_payload
from pipeline_backend.tools.gemini_client import GeminiClient


EXTRACTION_PROMPT = """
You are an expert financial information extraction system specializing in banking investor presentations.

Your task is to extract structured financial metrics exactly as they appear in the document.

IMPORTANT INSTRUCTIONS

1. Read EVERY slide before producing the final output.
2. For every target metric, extract ALL fiscal years that are explicitly present (FY22, FY23, FY24, FY25, etc.).
3. Never discard historical years because a newer year exists.
4. If a metric appears in multiple tables, use the table containing the most complete fiscal-year history.
5. Preserve values exactly as shown. Do not perform calculations, conversions, or normalization.
6. Return ONLY valid JSON.

Return JSON in the following format:

{
  "bank_name": "string",

  "financials": {
    "Metric Name": {
      "FY22": number_or_string_or_null,
      "FY23": number_or_string_or_null,
      "FY24": number_or_string_or_null,
      "FY25": number_or_string_or_null
    }
  },

  "metrics": [
    {
      "metric": "Metric Name",

      "values": {
        "FY22": number_or_string_or_null,
        "FY23": number_or_string_or_null,
        "FY24": number_or_string_or_null,
        "FY25": number_or_string_or_null
      },

      "source": {
        "page": integer,
        "slide": integer,
        "source_text": "short verbatim snippet containing the extracted values"
      },

      "confidence": 0.0
    }
  ]
}

Target metrics include (but are not limited to):

- Total Income
- Interest Income
- Other Income / Non Interest Income
- Total Expenditure
- Interest Expended
- Operating Expenses
- Provisions and Contingencies / Provisions Before Tax
- PAT / Net Profit
- NIM / Net Interest Margin
- ROA / Return on Assets
- ROE / Return on Equity
- Efficiency Ratio / Cost to Income Ratio
- GNPA
- NNPA
- CASA
- CRAR
- LCR
- Bank Z Score

EXTRACTION RULES

- Extract every fiscal year visible for every metric.
- Missing years should be null.
- Preserve the original units exactly as shown.
- Never convert decimals to percentages or percentages to decimals.
- Never remove commas or unit suffixes from string values if they appear in the document.
- Do not infer or estimate missing values.
- Do not merge information from different tables.

IMPORTANT FOR AMBIGUOUS METRICS

If both an amount and a percentage are present, treat them as separate metrics and preserve their original names exactly.

Examples:

- "Gross NPA (%)" and "Gross NPA (Amount)" are different metrics.
- "Net NPA (%)" and "Net NPA (Amount)" are different metrics.
- "CASA (%)" and "CASA (Amount)" are different metrics.
- "Capital Adequacy Basel III (%)" and "Total Capital" are different metrics.

Do NOT rename or merge these metrics.

The "metric" field should contain the exact metric name shown in the presentation.

Every entry in the metrics array must exactly match the corresponding entry in the financials dictionary.
"""


class GeminiFinancialExtractor:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    def extract(self, presentation_path: Path) -> ExtractedFinancials:
        payload = self.client.generate_json_from_file(presentation_path, EXTRACTION_PROMPT)
        return normalize_extracted_payload(payload)

