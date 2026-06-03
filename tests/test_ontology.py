import unittest

from ects_analysis.ontology import OntologyCycleError, TopicsOntology


class TopicsOntologyTests(unittest.TestCase):
    def test_topic_can_have_multiple_parents(self) -> None:
        ontology = TopicsOntology()
        ai = ontology.add_topic("Artificial Intelligence")
        data_center = ontology.add_topic("Data Center")
        workloads = ontology.add_topic("Generative AI Workloads", parent_ids=[ai, data_center])

        self.assertEqual(set(ontology.parent_ids(workloads)), {ai, data_center})

    def test_cycle_is_rejected(self) -> None:
        ontology = TopicsOntology()
        parent = ontology.add_topic("Operations")
        child = ontology.add_topic("Supply Chain")
        ontology.add_edge(parent, child)

        with self.assertRaises(OntologyCycleError):
            ontology.add_edge(child, parent)

    def test_alias_lookup_points_to_existing_topic(self) -> None:
        ontology = TopicsOntology()
        topic_id = ontology.add_topic("Mergers and Acquisitions")
        ontology.add_alias(topic_id, "M&A")

        self.assertEqual(ontology.find_topic_id("M&A"), topic_id)


if __name__ == "__main__":
    unittest.main()

