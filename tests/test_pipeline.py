import json
import re
import unittest

from ects_analysis.demo import build_system


class FakeOpenRouterClient:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"{system_prompt}\n{user_prompt}".casefold()
        if "topic existence agent" in prompt:
            query = self._line_value(user_prompt, "Query topic")
            references = self._bullets(user_prompt)
            matches = [
                {"topic": reference, "similarity": 100}
                for reference in references
                if self._normalize(reference) == self._normalize(query)
            ]
            return json.dumps(
                {
                    "query_topic": query,
                    "matches": matches,
                    "detailed_analysis": {"matched_topics": []},
                }
            )
        if "ontologist agent" in prompt:
            topic = self._line_value(user_prompt, "Given topic")
            topic_norm = self._normalize(topic)
            rules = {
                "Artificial Intelligence": ["ai", "generative ai"],
                "Data Center": ["data center"],
                "Financial Performance": ["revenue", "capital expenditures"],
                "Operations": ["supply chain"],
            }
            parents = [
                parent
                for parent, terms in rules.items()
                if parent in user_prompt and any(term in topic_norm for term in terms)
            ]
            return json.dumps({"reasoning": "test fixture", "parents": parents})
        return json.dumps(
            [
                {
                    "topic_name": "Data Center Revenue",
                    "excerpts": ["Data center revenue grew."],
                },
                {
                    "topic_name": "Generative AI Workloads",
                    "excerpts": ["Customers expanded capacity for generative AI workloads."],
                },
                {
                    "topic_name": "Supply Chain",
                    "excerpts": ["Supply chain lead times improved."],
                },
                {
                    "topic_name": "Capital Expenditures",
                    "excerpts": ["Capital expenditures will rise."],
                },
            ]
        )

    def _line_value(self, text: str, label: str) -> str:
        pattern = rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _bullets(self, text: str) -> list[str]:
        return [
            match.group(1).strip()
            for match in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", text, flags=re.MULTILINE)
        ]

    def _normalize(self, value: str) -> str:
        return " ".join(value.casefold().replace("&", "and").split())


class PipelineTests(unittest.TestCase):
    def test_dummy_document_builds_dag_assignments(self) -> None:
        document = (
            "Data center revenue grew as customers expanded capacity for generative AI workloads. "
            "Supply chain lead times improved. Capital expenditures will rise."
        )
        retriever, ontologist, ontology = build_system(llm_client=FakeOpenRouterClient())

        retrieved = retriever.retrieve(document)
        assignments = ontologist.enrich_topics(retrieved)

        self.assertGreaterEqual(len(retrieved), 3)
        self.assertEqual(len(assignments), len(retrieved))
        topic = ontology.get_node_by_name("Generative AI Workloads")
        self.assertIsNotNone(topic)
        self.assertGreaterEqual(len(ontology.parent_ids(topic.topic_id)), 1)


if __name__ == "__main__":
    unittest.main()
