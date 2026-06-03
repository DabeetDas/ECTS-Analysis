import unittest

from ects_analysis.visualize import render_corpus_html


class CorpusDashboardTests(unittest.TestCase):
    def test_render_corpus_html_displays_core_analysis_sections(self) -> None:
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
        }

        output = render_corpus_html(payload, title="PSB Corpus Analysis")

        self.assertIn("Trend Analysis", output)
        self.assertIn("Analyst Read", output)
        self.assertIn("Bank Overview", output)
        self.assertIn("Competitor Analysis", output)
        self.assertIn("Common Topics Between Banks", output)
        self.assertIn("Unique Topics By Bank", output)
        self.assertIn("State Bank of India", output)
        self.assertIn("scope=\"row\"", output)
        self.assertIn("Digital Banking", output)
        self.assertIn("1.0000", output)


if __name__ == "__main__":
    unittest.main()
