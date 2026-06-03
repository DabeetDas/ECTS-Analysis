from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4


def normalize_topic_name(value: str) -> str:
    return " ".join(value.casefold().replace("&", "and").split())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TopicNode:
    topic_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    created_on: str = field(default_factory=utc_now_iso)
    updated_on: str = field(default_factory=utc_now_iso)

    def add_alias(self, alias: str) -> None:
        if normalize_topic_name(alias) == normalize_topic_name(self.name):
            return
        if normalize_topic_name(alias) in {normalize_topic_name(a) for a in self.aliases}:
            return
        self.aliases.append(alias)
        self.updated_on = utc_now_iso()


class OntologyCycleError(ValueError):
    """Raised when adding an edge would break DAG invariants."""


class TopicsOntology:
    """Topic ontology backed by a directed acyclic graph.

    Edges point from broader parent topics to more specific child topics.
    A child can have multiple parents, which is the main difference from the
    tree structure described in the paper.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, TopicNode] = {}
        self.children: dict[str, set[str]] = {}
        self.parents: dict[str, set[str]] = {}
        self._name_index: dict[str, str] = {}

    @classmethod
    def with_seed_topics(cls, seed_topics: dict[str, list[str]]) -> "TopicsOntology":
        ontology = cls()
        for parent_name, child_names in seed_topics.items():
            parent_id = ontology.add_topic(parent_name)
            for child_name in child_names:
                child_id = ontology.add_topic(child_name)
                ontology.add_edge(parent_id, child_id)
        return ontology

    def add_topic(
        self,
        name: str,
        aliases: Iterable[str] | None = None,
        parent_ids: Iterable[str] | None = None,
    ) -> str:
        normalized = normalize_topic_name(name)
        if normalized in self._name_index:
            topic_id = self._name_index[normalized]
            for alias in aliases or []:
                self.add_alias(topic_id, alias)
            for parent_id in parent_ids or []:
                self.add_edge(parent_id, topic_id)
            return topic_id

        topic_id = str(uuid4())
        node = TopicNode(topic_id=topic_id, name=name)
        self.nodes[topic_id] = node
        self.children[topic_id] = set()
        self.parents[topic_id] = set()
        self._name_index[normalized] = topic_id

        for alias in aliases or []:
            self.add_alias(topic_id, alias)
        for parent_id in parent_ids or []:
            self.add_edge(parent_id, topic_id)
        return topic_id

    def add_alias(self, topic_id: str, alias: str) -> None:
        self._require_topic(topic_id)
        normalized = normalize_topic_name(alias)
        existing_id = self._name_index.get(normalized)
        if existing_id is not None and existing_id != topic_id:
            raise ValueError(f"Alias '{alias}' already belongs to another topic")
        self.nodes[topic_id].add_alias(alias)
        self._name_index[normalized] = topic_id

    def add_edge(self, parent_id: str, child_id: str) -> None:
        self._require_topic(parent_id)
        self._require_topic(child_id)
        if parent_id == child_id:
            raise OntologyCycleError("A topic cannot be its own parent")
        if self.has_path(child_id, parent_id):
            parent = self.nodes[parent_id].name
            child = self.nodes[child_id].name
            raise OntologyCycleError(f"Adding {parent} -> {child} would create a cycle")
        self.children[parent_id].add(child_id)
        self.parents[child_id].add(parent_id)
        self.nodes[parent_id].updated_on = utc_now_iso()
        self.nodes[child_id].updated_on = utc_now_iso()

    def find_topic_id(self, name_or_alias: str) -> str | None:
        return self._name_index.get(normalize_topic_name(name_or_alias))

    def get_node(self, topic_id: str) -> TopicNode:
        self._require_topic(topic_id)
        return self.nodes[topic_id]

    def get_node_by_name(self, name_or_alias: str) -> TopicNode | None:
        topic_id = self.find_topic_id(name_or_alias)
        return self.nodes[topic_id] if topic_id else None

    def topic_names(self) -> list[str]:
        return sorted(node.name for node in self.nodes.values())

    def root_ids(self) -> list[str]:
        return sorted(
            [topic_id for topic_id in self.nodes if not self.parents[topic_id]],
            key=lambda topic_id: self.nodes[topic_id].name,
        )

    def child_ids(self, topic_id: str) -> list[str]:
        self._require_topic(topic_id)
        return sorted(self.children[topic_id], key=lambda child_id: self.nodes[child_id].name)

    def parent_ids(self, topic_id: str) -> list[str]:
        self._require_topic(topic_id)
        return sorted(self.parents[topic_id], key=lambda parent_id: self.nodes[parent_id].name)

    def has_path(self, start_id: str, target_id: str) -> bool:
        self._require_topic(start_id)
        self._require_topic(target_id)
        stack = list(self.children[start_id])
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current == target_id:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.children[current])
        return False

    def as_parent_child_map(self) -> dict[str, list[str]]:
        return {
            self.nodes[parent_id].name: [self.nodes[child_id].name for child_id in self.child_ids(parent_id)]
            for parent_id in sorted(self.nodes, key=lambda topic_id: self.nodes[topic_id].name)
            if self.children[parent_id]
        }

    def to_dict(self) -> dict[str, object]:
        edges = [
            {
                "parent_id": parent_id,
                "parent_name": self.nodes[parent_id].name,
                "child_id": child_id,
                "child_name": self.nodes[child_id].name,
            }
            for parent_id in sorted(self.children)
            for child_id in sorted(self.children[parent_id])
        ]
        return {
            "nodes": [asdict(node) for node in sorted(self.nodes.values(), key=lambda n: n.name)],
            "edges": edges,
            "roots": [self.nodes[topic_id].name for topic_id in self.root_ids()],
        }

    def _require_topic(self, topic_id: str) -> None:
        if topic_id not in self.nodes:
            raise KeyError(f"Unknown topic id: {topic_id}")

