from __future__ import annotations

import json
from dataclasses import dataclass

from ects_analysis.llm import LLMClient, normalize_json_response
from ects_analysis.ontology import OntologyCycleError, TopicsOntology
from ects_analysis.prompts import DAG_TOPIC_INSERTION_PROMPT, TOPIC_EXISTENCE_PROMPT
from ects_analysis.retriever import RetrievedTopic


@dataclass(frozen=True)
class OntologyAssignment:
    topic_id: str
    topic_name: str
    excerpts: list[str]
    existed: bool
    parent_topic_ids: list[str]


class OntologistAgent:
    """Maintains topic existence and insertion workflows from Section 3.4."""

    def __init__(
        self,
        ontology: TopicsOntology,
        llm_client: LLMClient,
        similarity_threshold: int = 90,
    ) -> None:
        self.ontology = ontology
        self.llm_client = llm_client
        self.similarity_threshold = similarity_threshold

    def enrich_topics(self, retrieved_topics: list[RetrievedTopic]) -> list[OntologyAssignment]:
        return [self.ensure_topic(topic) for topic in retrieved_topics]

    def ensure_topic(self, retrieved_topic: RetrievedTopic) -> OntologyAssignment:
        existing_id = self.ontology.find_topic_id(retrieved_topic.topic_name)
        if existing_id:
            return self._assignment(existing_id, retrieved_topic, existed=True)

        semantic_match_id = self._find_semantic_equivalent(retrieved_topic.topic_name)
        if semantic_match_id:
            self.ontology.add_alias(semantic_match_id, retrieved_topic.topic_name)
            return self._assignment(semantic_match_id, retrieved_topic, existed=True)

        parent_ids = self._choose_parent_ids(retrieved_topic.topic_name)
        topic_id = self.ontology.add_topic(retrieved_topic.topic_name)
        for parent_id in parent_ids:
            try:
                self.ontology.add_edge(parent_id, topic_id)
            except OntologyCycleError:
                continue
        return self._assignment(topic_id, retrieved_topic, existed=False)

    def _find_semantic_equivalent(self, topic_name: str) -> str | None:
        reference_labels = self._reference_topic_labels()
        if not reference_labels:
            return None
        user_prompt = "\n".join(
            [
                "Reference ontology topic names and aliases:",
                *[f"- {topic}" for topic in reference_labels],
                f"Query topic: {topic_name}",
            ]
        )
        try:
            response = self.llm_client.complete(
                system_prompt=TOPIC_EXISTENCE_PROMPT,
                user_prompt=user_prompt,
            )
            payload = json.loads(normalize_json_response(response))
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            return None
        valid_matches = [match for match in matches if isinstance(match, dict)]
        for match in sorted(valid_matches, key=lambda item: item.get("similarity", 0), reverse=True):
            topic = match.get("topic")
            similarity = match.get("similarity", 0)
            if isinstance(topic, str) and similarity >= self.similarity_threshold:
                return self.ontology.find_topic_id(topic)
        return None

    def _choose_parent_ids(self, topic_name: str) -> list[str]:
        if not self.ontology.nodes:
            return []
        user_prompt = "\n".join(
            [
                f"Given topic: {topic_name}",
                "Topic DAG:",
                json.dumps(self.ontology.as_parent_child_map(), indent=2, sort_keys=True),
                "Available parent topics:",
                *[f"- {topic}" for topic in self.ontology.topic_names()],
            ]
        )
        try:
            response = self.llm_client.complete(
                system_prompt=DAG_TOPIC_INSERTION_PROMPT,
                user_prompt=user_prompt,
            )
            payload = json.loads(normalize_json_response(response))
        except (json.JSONDecodeError, ValueError):
            return []
        if isinstance(payload, dict):
            parents = payload.get("parents", [])
        elif isinstance(payload, list):
            parents = payload
        else:
            parents = []
        if not isinstance(parents, list):
            return []

        parent_ids: list[str] = []
        for parent in parents:
            if isinstance(parent, dict):
                parent = parent.get("topic") or parent.get("parent") or parent.get("name")
            if not isinstance(parent, str):
                continue
            parent_id = self.ontology.find_topic_id(parent)
            if parent_id and parent_id not in parent_ids:
                parent_ids.append(parent_id)
        return parent_ids

    def _assignment(
        self,
        topic_id: str,
        retrieved_topic: RetrievedTopic,
        existed: bool,
    ) -> OntologyAssignment:
        node = self.ontology.get_node(topic_id)
        return OntologyAssignment(
            topic_id=topic_id,
            topic_name=node.name,
            excerpts=retrieved_topic.excerpts,
            existed=existed,
            parent_topic_ids=self.ontology.parent_ids(topic_id),
        )

    def _reference_topic_labels(self) -> list[str]:
        labels: list[str] = []
        for node in sorted(self.ontology.nodes.values(), key=lambda item: item.name):
            labels.append(node.name)
            labels.extend(node.aliases)
        return labels
