from __future__ import annotations

import json
from dataclasses import dataclass

from ects_analysis.llm import LLMClient, normalize_json_response
from ects_analysis.prompts import TOPIC_RETRIEVAL_PROMPT


@dataclass(frozen=True)
class RetrievedTopic:
    topic_name: str
    excerpts: list[str]


class TopicRetriever:
    """LLM-backed topic retriever from Section 3.2."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def retrieve(self, document_text: str) -> list[RetrievedTopic]:
        response = self.llm_client.complete(
            system_prompt=TOPIC_RETRIEVAL_PROMPT,
            user_prompt=f"Document text:\n<document>\n{document_text}\n</document>",
        )
        payload = json.loads(normalize_json_response(response))
        if not isinstance(payload, list):
            raise ValueError("Topic retriever expected a JSON array")

        topics = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("Each retrieved topic must be a JSON object")
            topic_name = item.get("topic_name")
            excerpts = item.get("excerpts", [])
            if not isinstance(topic_name, str) or not topic_name.strip():
                raise ValueError("Retrieved topic is missing `topic_name`")
            if not isinstance(excerpts, list) or not all(isinstance(e, str) for e in excerpts):
                raise ValueError("Retrieved topic `excerpts` must be a list of strings")
            topics.append(RetrievedTopic(topic_name=topic_name.strip(), excerpts=excerpts))
        return topics
