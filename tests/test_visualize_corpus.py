import json
from pathlib import Path
import tempfile
import unittest

from ects_analysis.visualize import (
    export_dashboard_payload,
    load_financial_analysis,
    write_dashboard_payload,
)


class CorpusDashboardTests(unittest.TestCase):
    def test_export_dashboard_payload_includes_frontend_sections(self) -> None:
        payload = {
            "parameters": {"top_n": 100, "alpha": 0.05},
            "documents": [
                {
                    "company": "SBI",
                    "quarter": "FY24 Q4",
                    "call_date": "2024-05-09",
                    "path": "psb_calls/SBI_2024-05-09.txt",
                }
            ],
            "observations": [
                {
                    "company": "SBI",
                    "quarter": "FY24 Q4",
                    "call_date": "2024-05-09",
                    "topic_name": "Digital Banking",
                    "mention_count": 3,
                    "excerpts": ["Digital transactions increased."],
                }
            ],
            "trend_analysis": {
                "SBI": [
                    {
                        "topic_name": "Digital Banking",
                        "direction": "up",
                        "kendall_tau": 1.0,
                        "p_value": 0.01,
                        "series": [
                            {"call_date": "2024-05-09", "mention_count": 3},
                        ],
                        "sample_excerpts": ["Digital transactions increased."],
                    }
                ]
            },
            "competitor_analysis": {
                "jaccard_similarity": {"SBI": {"SBI": 1.0}},
                "common_topics": {},
                "unique_topics": {
                    "SBI": [
                        {
                            "topic_name": "Digital Banking",
                            "mention_count": 3,
                            "sample_excerpts": ["Digital transactions increased."],
                        }
                    ]
                },
                "top_topics_by_company": {
                    "SBI": [{"topic_name": "Digital Banking", "mention_count": 3}]
                },
            },
            "financial_analysis": {
                "SBI": [
                    {
                        "bank": "SBI",
                        "fiscal_year": "FY24",
                        "total_business_cr": "1000",
                        "profit_after_tax_cr": "100",
                        "roa_pct": "1.0",
                        "nim_pct": "3.1",
                        "gnpa_pct": "2.0",
                        "nnpa_pct": "0.5",
                        "casa_pct": "40.0",
                        "credit_cost_pct": "0.5",
                        "crar_pct": "14.0",
                        "lcr_pct": "120.0",
                    },
                    {
                        "bank": "SBI",
                        "fiscal_year": "FY25",
                        "total_business_cr": "1200",
                        "profit_after_tax_cr": "130",
                        "roa_pct": "1.1",
                        "nim_pct": "3.2",
                        "gnpa_pct": "1.5",
                        "nnpa_pct": "0.4",
                        "casa_pct": "41.0",
                        "credit_cost_pct": "0.4",
                        "crar_pct": "14.5",
                        "lcr_pct": "122.0",
                    },
                ]
            },
        }

        output = export_dashboard_payload(
            payload,
            financial_analysis=payload["financial_analysis"],
            topic_hierarchy={"Digital and Operations": ["Digital Banking"]},
            profile_bank="SBI",
        )

        self.assertEqual(output["metadata"]["profile_bank"], "SBI")
        self.assertEqual(output["banks"]["SBI"]["label"], "State Bank of India")
        self.assertIn("Digital and Operations", output["topic_hierarchy"])
        self.assertEqual(len(output["financial_analysis"]["SBI"]), 2)
        self.assertEqual(
            output["analysis"]["competitor_analysis"]["jaccard_similarity"]["SBI"]["SBI"],
            1.0,
        )
        self.assertEqual(
            output["analysis"]["observations"][0]["topic_name"],
            "Digital Banking",
        )

    def test_load_financial_analysis_groups_rows_by_bank(self) -> None:
        financials = load_financial_analysis(Path("data/psb_financials_dummy.csv"))

        self.assertIn("BOB", financials)
        self.assertEqual(len(financials["BOB"]), 3)
        self.assertEqual(financials["BOB"][-1]["fiscal_year"], "FY25")

    def test_load_financial_analysis_reads_sbi_bob_excel_workbook(self) -> None:
        try:
            import openpyxl
        except ImportError as exc:
            raise unittest.SkipTest("openpyxl is not installed") from exc

        workbook = openpyxl.Workbook()
        high_level = workbook.active
        high_level.title = "High level comparison"
        high_level.append([None, None, None, "SBI", "Bank of Baroda"])
        high_level.append([None, "Profit", "Net profit", 709006281000, 195811521000])

        for sheet_name, nim, gnpa in [
            ("SBI", 0.0309, 0.0182),
            ("Bank of Baroda", 0.0274, 0.0226),
        ]:
            sheet = workbook.create_sheet(sheet_name)
            sheet.append([None, None, "Key Financial Ratios"])
            sheet.append([None, None, None, None, "As at 31.03.2025", "As at 31.03.2024"])
            sheet.append([None, None, "Profitability Ratios", "Net Interest Margin", nim, 0.0303])
            sheet.append([None, None, "Asset Quality", "Gross Non Performing Assets (GNPA)", gnpa, 0.0292])

        with tempfile.TemporaryDirectory() as directory:
            workbook_path = Path(directory) / "financials.xlsx"
            workbook.save(workbook_path)
            financials = load_financial_analysis(workbook_path)

        self.assertEqual(financials["SBI"][-1]["fiscal_year"], "FY25")
        self.assertEqual(financials["SBI"][-1]["nim_pct"], "3.09")
        self.assertEqual(financials["SBI"][-1]["profit_after_tax_cr"], "70900.63")
        self.assertEqual(financials["BOB"][-1]["gnpa_pct"], "2.26")
        self.assertEqual(financials["BOB"][-1]["profit_after_tax_cr"], "19581.15")

    def test_write_dashboard_payload_preserves_existing_qualitative_when_input_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base_path = Path(directory)
            input_path = base_path / "empty_analysis.json"
            output_path = base_path / "dashboard-data.json"
            financials_path = base_path / "financials.csv"
            hierarchy_path = base_path / "topics.json"

            input_path.write_text(
                """{
  "documents": [{"company": "SBI", "call_date": "2025-01-01"}],
  "observations": [],
  "trend_analysis": {},
  "competitor_analysis": {}
}""",
                encoding="utf-8",
            )
            output_path.write_text(
                """{
  "metadata": {"title": "Existing", "profile_bank": "SBI"},
  "banks": {},
  "topic_hierarchy": {},
  "financial_analysis": {},
  "analysis": {
    "documents": [{"company": "SBI", "call_date": "2024-05-09"}],
    "observations": [{"company": "SBI", "call_date": "2024-05-09", "topic_name": "Digital Banking", "mention_count": 2}],
    "trend_analysis": {"SBI": []},
    "competitor_analysis": {"top_topics_by_company": {"SBI": []}}
  }
}""",
                encoding="utf-8",
            )
            financials_path.write_text(
                "bank,fiscal_year,profit_after_tax_cr\nSBI,FY25,100\n",
                encoding="utf-8",
            )
            hierarchy_path.write_text('{"Digital and Operations": ["Digital Banking"]}', encoding="utf-8")

            write_dashboard_payload(
                input_path=input_path,
                output_path=output_path,
                financials_path=financials_path,
                topic_hierarchy_path=hierarchy_path,
                profile_bank="SBI",
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["analysis"]["observations"][0]["topic_name"], "Digital Banking")
        self.assertEqual(payload["financial_analysis"]["SBI"][0]["profit_after_tax_cr"], "100")


if __name__ == "__main__":
    unittest.main()
