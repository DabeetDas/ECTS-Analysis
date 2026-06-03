import json
import unittest

from ects_analysis.ontology import TopicsOntology
from ects_analysis.ontologist import OntologistAgent
from ects_analysis.retriever import RetrievedTopic


class SequenceClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return json.dumps(response)


class RawSequenceClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return response


class OntologistAgentParsingTests(unittest.TestCase):
    def test_parent_selection_accepts_list_response_from_llm(self) -> None:
        ontology = TopicsOntology()
        ontology.add_topic("Banking Operations")
        agent = OntologistAgent(
            ontology=ontology,
            llm_client=SequenceClient(
                [
                    [],
                    ["Banking Operations"],
                ]
            ),
        )

        assignment = agent.ensure_topic(RetrievedTopic("Digital Banking", ["Digital apps grew."]))

        self.assertEqual(assignment.topic_name, "Digital Banking")
        self.assertEqual(len(assignment.parent_topic_ids), 1)

    def test_existence_check_ignores_non_object_response(self) -> None:
        ontology = TopicsOntology()
        agent = OntologistAgent(
            ontology=ontology,
            llm_client=SequenceClient(
                [
                    [],
                    [],
                ]
            ),
        )

        assignment = agent.ensure_topic(RetrievedTopic("CASA", ["CASA improved."]))

        self.assertEqual(assignment.topic_name, "CASA")
        self.assertEqual(assignment.parent_topic_ids, [])

    def test_malformed_existence_response_falls_back_to_new_topic(self) -> None:
        ontology = TopicsOntology()
        agent = OntologistAgent(
            ontology=ontology,
            llm_client=RawSequenceClient(
                [
                    "not json",
                    '{"parents": []}',
                ]
            ),
        )

        assignment = agent.ensure_topic(RetrievedTopic("CASA", ["CASA improved."]))

        self.assertEqual(assignment.topic_name, "CASA")
        self.assertEqual(assignment.parent_topic_ids, [])

    def test_malformed_parent_response_uses_no_parents(self) -> None:
        ontology = TopicsOntology()
        ontology.add_topic("Banking Operations")
        agent = OntologistAgent(
            ontology=ontology,
            llm_client=RawSequenceClient(
                [
                    '{"matches": []}',
                    "not json",
                ]
            ),
        )

        assignment = agent.ensure_topic(RetrievedTopic("Digital Banking", ["Digital apps grew."]))

        self.assertEqual(assignment.topic_name, "Digital Banking")
        self.assertEqual(assignment.parent_topic_ids, [])


if __name__ == "__main__":
    unittest.main()
