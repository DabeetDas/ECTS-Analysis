import unittest

from pipeline_backend.schemas import TranscriptChunk
from pipeline_backend.tools.transcript_search import retrieve_metric_evidence


class TranscriptSearchTests(unittest.TestCase):
    def test_retrieve_metric_evidence_scores_direct_asset_quality_commentary(self) -> None:
        chunks = [
            TranscriptChunk(
                chunk_id="chunk_1",
                text=(
                    "Management said GNPA declined because asset quality improved and recoveries were strong. "
                    "Deposit growth was stable during the quarter."
                ),
            )
        ]

        evidence = retrieve_metric_evidence(metric_key="gnpa_pct", chunks=chunks)

        self.assertTrue(evidence)
        self.assertEqual(evidence[0].match_type, "direct")
        self.assertIn("GNPA", evidence[0].excerpt)


if __name__ == "__main__":
    unittest.main()
