import unittest

from pipeline_backend.tools.financial_normalizer import normalize_extracted_payload, resolve_metric_key


class FinancialNormalizerTests(unittest.TestCase):
    def test_normalize_extracted_payload_maps_data_new_style_metrics(self) -> None:
        payload = {
            "bank_name": "Example Bank",
            "financials": {
                "Net profit": {"FY25": 195811521000},
                "Net Interest Margin": {"FY24": 0.0303, "FY25": 0.0274},
                "Gross Non Performing Assets": {"FY25": "2.26%"},
            },
        }

        result = normalize_extracted_payload(payload)
        by_key_period = {(metric.metric_key, metric.period): metric.value for metric in result.metrics}

        self.assertEqual(result.bank_name, "Example Bank")
        self.assertEqual(by_key_period[("profit_after_tax_cr", "FY25")], 19581.15)
        self.assertEqual(by_key_period[("nim_pct", "FY25")], 2.74)
        self.assertEqual(by_key_period[("gnpa_pct", "FY25")], 2.26)

    def test_resolve_metric_key_handles_aliases(self) -> None:
        self.assertEqual(resolve_metric_key("Capital to Risk Weight Assets Ratio"), "crar_pct")
        self.assertEqual(resolve_metric_key("Cost to Income Ratio"), "efficiency_ratio_pct")


if __name__ == "__main__":
    unittest.main()
