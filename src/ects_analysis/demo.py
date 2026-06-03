from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ects_analysis.llm import (
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TRANSFORMERS_MODEL,
    LLMClient,
    OllamaClient,
    OpenRouterClient,
    QwenTransformersClient,
)
from ects_analysis.ontology import TopicsOntology
from ects_analysis.ontologist import OntologistAgent
from ects_analysis.retriever import TopicRetriever


DEFAULT_SEED_TOPICS = {
    "Artificial Intelligence": ["Generative AI", "Machine Learning"],
    "Data Center": ["Cloud Infrastructure", "Enterprise Demand"],
    "Operations": ["Supply Chain", "Manufacturing"],
    "Financial Performance": ["Revenue", "Capital Allocation"],
    "Automotive": ["Autonomous Driving", "Electric Vehicles"],
    "Legal and Regulatory": ["Regulatory Developments"],
}


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def build_system(
    llm_client: LLMClient | None = None,
    model: str = DEFAULT_OPENROUTER_MODEL,
    provider: str = "openrouter",
    seed_topics: dict[str, list[str]] | None = None,
) -> tuple[TopicRetriever, OntologistAgent, TopicsOntology]:
    llm = llm_client or build_llm_client(provider=provider, model=model)
    ontology = TopicsOntology.with_seed_topics(seed_topics or DEFAULT_SEED_TOPICS)
    retriever = TopicRetriever(llm)
    ontologist = OntologistAgent(ontology=ontology, llm_client=llm)
    return retriever, ontologist, ontology


def build_llm_client(provider: str, model: str) -> LLMClient:
    normalized_provider = provider.casefold()
    if normalized_provider == "openrouter":
        return OpenRouterClient(model=model, api_key=os.environ.get("OPENROUTER_API_KEY"))
    if normalized_provider == "ollama":
        return OllamaClient(model=model, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    if normalized_provider == "qwen":
        if model == DEFAULT_OPENROUTER_MODEL:
            model = DEFAULT_TRANSFORMERS_MODEL
        return QwenTransformersClient(
            model=model,
            max_input_tokens=int(os.environ.get("TRANSFORMERS_MAX_INPUT_TOKENS", "32768")),
            max_tokens=int(os.environ.get("TRANSFORMERS_MAX_NEW_TOKENS", "4096")),
            generation_max_time_seconds=env_optional_float(
                "TRANSFORMERS_GENERATION_MAX_TIME_SECONDS"
            ),
            device_map=os.environ.get("TRANSFORMERS_DEVICE_MAP", "auto"),
            torch_dtype=os.environ.get("TRANSFORMERS_TORCH_DTYPE", "auto"),
            trust_remote_code=env_flag("TRANSFORMERS_TRUST_REMOTE_CODE", default=False),
            local_files_only=env_flag("TRANSFORMERS_LOCAL_FILES_ONLY", default=True),
            load_in_4bit=env_flag("TRANSFORMERS_LOAD_IN_4BIT", default=False),
            load_in_8bit=env_flag("TRANSFORMERS_LOAD_IN_8BIT", default=False),
            enable_thinking=env_flag("TRANSFORMERS_ENABLE_THINKING", default=False),
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def env_flag(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes"}


def env_optional_float(name: str) -> float | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    parsed = float(value)
    return parsed if parsed > 0 else None


def load_seed_topics(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return DEFAULT_SEED_TOPICS
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Seed topics JSON must be an object of parent topic to child topic list")
    seed_topics: dict[str, list[str]] = {}
    for parent, children in payload.items():
        if not isinstance(parent, str) or not isinstance(children, list):
            raise ValueError("Seed topics JSON must map strings to lists of strings")
        if not all(isinstance(child, str) for child in children):
            raise ValueError("Seed topic child lists must contain only strings")
        seed_topics[parent] = children
    return seed_topics


def main() -> None:
    load_dotenv_if_available()
    parser = argparse.ArgumentParser(description="Run topic retrieval and DAG ontology insertion.")
    parser.add_argument("--input", default="data/dummy_earnings_call.txt", help="Input text document")
    parser.add_argument("--output", default="outputs/ontology.json", help="Output ontology JSON")
    parser.add_argument(
        "--model",
        default=DEFAULT_OPENROUTER_MODEL,
        help="OpenRouter/Ollama model name, or a local Qwen Transformers checkpoint directory",
    )
    parser.add_argument(
        "--provider",
        choices=["openrouter", "ollama", "qwen"],
        default=os.environ.get("LLM_PROVIDER", "openrouter"),
        help="LLM provider to use",
    )
    parser.add_argument("--seed-topics", default="data/seed_topics.json", help="Initial root and child topics JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    seed_topics_path = Path(args.seed_topics) if args.seed_topics else None
    document_text = input_path.read_text(encoding="utf-8")
    seed_topics = load_seed_topics(seed_topics_path)

    retriever, ontologist, ontology = build_system(
        model=args.model,
        provider=args.provider,
        seed_topics=seed_topics,
    )
    retrieved_topics = retriever.retrieve(document_text)
    assignments = ontologist.enrich_topics(retrieved_topics)

    output = {
        "input_document": str(input_path),
        "retrieved_topics": [
            {"topic_name": topic.topic_name, "excerpts": topic.excerpts}
            for topic in retrieved_topics
        ],
        "assignments": [
            {
                "topic_id": assignment.topic_id,
                "topic_name": assignment.topic_name,
                "existed": assignment.existed,
                "parent_topic_ids": assignment.parent_topic_ids,
                "excerpts": assignment.excerpts,
            }
            for assignment in assignments
        ],
        "ontology": ontology.to_dict(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Retrieved {len(retrieved_topics)} topics")
    print(f"Wrote DAG ontology to {output_path}")


if __name__ == "__main__":
    main()
