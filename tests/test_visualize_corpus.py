from pathlib import Path
import unittest

from ects_analysis.visualize import export_dashboard_payload, load_financial_analysis


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


if __name__ == "__main__":
    unittest.main()
