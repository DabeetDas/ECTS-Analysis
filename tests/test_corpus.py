import unittest
from datetime import date

from ects_analysis.corpus import (
    TopicObservation,
    assign_topic_without_llm,
    chunk_document_text,
    compute_competitor_analysis,
    compute_trends,
    jaccard_similarity,
    kendall_tau_trend,
    recompute_existing_analysis,
    retrieve_chunked_topics,
)
from ects_analysis.ontology import TopicsOntology
from ects_analysis.retriever import RetrievedTopic


def observation(
    company: str,
    call_date: str,
    topic_id: str,
    topic_name: str,
    count: int,
) -> TopicObservation:
    return TopicObservation(
        company=company,
        call_date=date.fromisoformat(call_date),
        quarter=None,
        topic_id=topic_id,
        topic_name=topic_name,
        mention_count=count,
        excerpts=[f"{company} discussed {topic_name}."],
    )


class CorpusAnalysisTests(unittest.TestCase):
    def test_chunk_document_text_splits_on_paragraph_boundaries(self) -> None:
        chunks = chunk_document_text("first paragraph\n\nsecond paragraph\n\nthird paragraph", chunk_chars=25)

        self.assertEqual(chunks, ["first paragraph", "second paragraph", "third paragraph"])
        self.assertTrue(all(len(chunk) <= 25 for chunk in chunks))

    def test_retrieve_chunked_topics_merges_duplicate_topic_excerpts(self) -> None:
        class FakeRetriever:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def retrieve(self, document_text: str) -> list[RetrievedTopic]:
                self.calls.append(document_text)
                return [RetrievedTopic("Digital Banking", [f"excerpt {len(self.calls)}"])]

        retriever = FakeRetriever()
        progress_calls: list[str] = []
        topics = retrieve_chunked_topics(
            retriever,
            "one paragraph\n\ntwo paragraph",
            chunk_chars=15,
            progress_callback=progress_calls.append,
        )

        self.assertEqual(len(retriever.calls), 2)
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].topic_name, "Digital Banking")
        self.assertEqual(topics[0].excerpts, ["excerpt 1", "excerpt 2"])

    def test_retrieve_chunked_topics_skips_failed_chunk(self) -> None:
        class FlakyRetriever:
            def __init__(self) -> None:
                self.calls = 0

            def retrieve(self, document_text: str) -> list[RetrievedTopic]:
                self.calls += 1
                if self.calls == 1:
                    raise ValueError("LLM response contained malformed JSON")
                return [RetrievedTopic("Deposits", ["Deposits grew."])]

        retriever = FlakyRetriever()
        topics = retrieve_chunked_topics(
            retriever,
            "one paragraph\n\ntwo paragraph",
            chunk_chars=15,
        )

        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].topic_name, "Deposits")

    def test_assign_topic_without_llm_reuses_exact_topic(self) -> None:
        ontology = TopicsOntology.with_seed_topics({"Banking": ["Deposits"]})

        existing = assign_topic_without_llm(ontology, RetrievedTopic("Deposits", ["Deposits grew."]))
        new = assign_topic_without_llm(ontology, RetrievedTopic("Asset Quality", ["GNPA improved."]))

        self.assertTrue(existing.existed)
        self.assertEqual(existing.topic_name, "Deposits")
        self.assertFalse(new.existed)
        self.assertEqual(new.topic_name, "Asset Quality")

    def test_kendall_tau_identifies_monotonic_direction(self) -> None:
        upward_tau, upward_p = kendall_tau_trend([0, 1, 2, 3, 4])
        downward_tau, downward_p = kendall_tau_trend([4, 3, 2, 1, 0])

        self.assertAlmostEqual(upward_tau, 1.0)
        self.assertAlmostEqual(downward_tau, -1.0)
        self.assertLess(upward_p, 0.05)
        self.assertLess(downward_p, 0.05)

    def test_compute_trends_returns_significant_topics_by_company(self) -> None:
        observations = [
            observation("SBI", "2024-01-01", "digital", "Digital Banking", 0),
            observation("SBI", "2024-04-01", "digital", "Digital Banking", 1),
            observation("SBI", "2024-07-01", "digital", "Digital Banking", 2),
            observation("SBI", "2024-10-01", "digital", "Digital Banking", 3),
            observation("SBI", "2025-01-01", "digital", "Digital Banking", 4),
        ]

        trends = compute_trends(observations, min_periods=4, alpha=0.05)

        self.assertEqual(trends["SBI"][0]["topic_name"], "Digital Banking")
        self.assertEqual(trends["SBI"][0]["direction"], "up")

    def test_competitor_analysis_uses_top_topic_jaccard_and_unique_topics(self) -> None:
        observations = [
            observation("SBI", "2024-01-01", "deposit", "Deposit Growth", 5),
            observation("SBI", "2024-01-01", "digital", "Digital Banking", 4),
            observation("PNB", "2024-01-01", "deposit", "Deposit Growth", 3),
            observation("PNB", "2024-01-01", "asset", "Asset Quality", 2),
        ]

        analysis = compute_competitor_analysis(observations, top_n=2)

        self.assertEqual(jaccard_similarity({"deposit", "digital"}, {"deposit", "asset"}), 1 / 3)
        self.assertAlmostEqual(analysis["jaccard_similarity"]["SBI"]["PNB"], 0.3333)
        self.assertEqual(analysis["common_topics"]["PNB__SBI"][0]["topic_name"], "Deposit Growth")
        self.assertEqual(analysis["unique_topics"]["SBI"][0]["topic_name"], "Digital Banking")
        self.assertEqual(analysis["unique_topics"]["PNB"][0]["topic_name"], "Asset Quality")

    def test_recompute_existing_analysis_reuses_observations_without_llm(self) -> None:
        payload = {
            "parameters": {"top_n": 2, "alpha": 1.0, "min_periods": 4},
            "observations": [
                {
                    "company": "SBI",
                    "call_date": "2024-01-01",
                    "quarter": "Q1",
                    "topic_id": "deposit",
                    "topic_name": "Deposit Growth",
                    "mention_count": 1,
                    "excerpts": ["Deposit growth was discussed."],
                },
                {
                    "company": "SBI",
                    "call_date": "2024-04-01",
                    "quarter": "Q2",
                    "topic_id": "deposit",
                    "topic_name": "Deposit Growth",
                    "mention_count": 3,
                    "excerpts": ["Deposit growth improved."],
                },
            ],
        }

        output = recompute_existing_analysis(payload, min_periods=2, alpha=1.0)

        self.assertEqual(output["parameters"]["min_periods"], 2)
        self.assertTrue(output["parameters"]["recomputed_from_existing_observations"])
        self.assertEqual(output["trend_analysis"]["SBI"][0]["topic_name"], "Deposit Growth")


if __name__ == "__main__":
    unittest.main()
