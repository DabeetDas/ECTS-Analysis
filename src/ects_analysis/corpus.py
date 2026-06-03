from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, TextIO

from ects_analysis.demo import build_system, load_dotenv_if_available, load_seed_topics
from ects_analysis.llm import DEFAULT_OPENROUTER_MODEL
from ects_analysis.ontology import TopicsOntology, normalize_topic_name
from ects_analysis.ontologist import OntologyAssignment
from ects_analysis.retriever import RetrievedTopic, TopicRetriever


ProgressCallback = Callable[[str], None]


class ProgressBar:
    def __init__(
        self,
        *,
        total: int,
        label: str = "Progress",
        stream: TextIO | None = None,
        width: int = 28,
        enabled: bool = True,
    ) -> None:
        self.total = max(0, total)
        self.label = label
        self.stream = stream or sys.stderr
        self.width = width
        self.enabled = enabled
        self.current = 0
        self._last_line_length = 0

    def advance(self, detail: str = "") -> None:
        if not self.enabled:
            return
        self.current = min(self.total, self.current + 1) if self.total else self.current + 1
        self._render(detail)

    def update(self, detail: str = "") -> None:
        if not self.enabled:
            return
        self._render(detail)

    def finish(self, detail: str = "done") -> None:
        if not self.enabled:
            return
        if self.total:
            self.current = self.total
        self._render(detail)
        self.stream.write("\n")
        self.stream.flush()

    def _render(self, detail: str) -> None:
        if self.total:
            filled = round(self.width * self.current / self.total)
            percent = round(100 * self.current / self.total)
            count = f"{self.current}/{self.total}"
        else:
            filled = self.width
            percent = 100
            count = "0/0"
        bar = "#" * filled + "-" * (self.width - filled)
        suffix = f" {detail}" if detail else ""
        line = f"{self.label} [{bar}] {count} {percent:3d}%{suffix}"
        padding = " " * max(0, self._last_line_length - len(line))
        self.stream.write(f"\r{line}{padding}")
        self._last_line_length = len(line)
        self.stream.flush()


@dataclass(frozen=True)
class CallDocument:
    company: str
    call_date: date
    path: Path
    quarter: str | None = None


@dataclass(frozen=True)
class TopicObservation:
    company: str
    call_date: date
    quarter: str | None
    topic_id: str
    topic_name: str
    mention_count: int
    excerpts: list[str]


def load_manifest(path: Path) -> list[CallDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Manifest must be a JSON array")

    documents: list[CallDocument] = []
    base_dir = path.parent
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Manifest row {index} must be an object")
        company = _required_string(item, "company", index)
        raw_date = _required_string(item, "call_date", index)
        raw_path = _required_string(item, "path", index)
        quarter = item.get("quarter")
        if quarter is not None and not isinstance(quarter, str):
            raise ValueError(f"Manifest row {index} field `quarter` must be a string")
        try:
            call_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError(f"Manifest row {index} has invalid `call_date`: {raw_date}") from exc

        document_path = Path(raw_path)
        if not document_path.is_absolute():
            document_path = base_dir / document_path
        documents.append(
            CallDocument(
                company=company.strip(),
                call_date=call_date,
                path=document_path,
                quarter=quarter.strip() if quarter else None,
            )
        )
    return sorted(documents, key=lambda document: (document.company, document.call_date))


def _required_string(item: dict[str, object], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Manifest row {index} is missing string field `{field}`")
    return value


def run_corpus_analysis(
    documents: Iterable[CallDocument],
    *,
    model: str,
    seed_topics: dict[str, list[str]],
    provider: str = "openrouter",
    top_n: int = 100,
    alpha: float = 0.05,
    min_periods: int = 4,
    exclude_topics: Iterable[str] = (),
    chunk_chars: int = 6000,
    request_delay_seconds: float = 0.0,
    slow_chunk_seconds: float = 60.0,
    slow_enrichment_seconds: float = 60.0,
    max_topics_per_document: int | None = None,
    use_ontology_llm: bool = True,
    show_progress: bool = False,
    progress_stream: TextIO | None = None,
) -> dict[str, object]:
    document_list = sorted(documents, key=lambda item: (item.company, item.call_date))
    excluded_topic_list = list(exclude_topics)
    retriever, ontologist, ontology = build_system(
        model=model,
        provider=provider,
        seed_topics=seed_topics,
    )
    observations: list[TopicObservation] = []

    document_chunks: list[tuple[CallDocument, list[str]]] = []
    for document in document_list:
        text = document.path.read_text(encoding="utf-8")
        document_chunks.append((document, chunk_document_text(text, chunk_chars=chunk_chars)))

    total_steps = sum(len(chunks) for _, chunks in document_chunks) + len(document_chunks)
    progress = ProgressBar(
        total=total_steps,
        label="Corpus LLM",
        stream=progress_stream,
        enabled=show_progress,
    )

    for document, chunks in document_chunks:
        chunk_total = len(chunks)
        chunk_index = 0

        def advance_progress(_: str) -> None:
            nonlocal chunk_index
            chunk_index += 1
            progress.advance(
                f"{document.company} {document.call_date.isoformat()} chunk {chunk_index}/{chunk_total}"
            )

        def start_progress(chunk: str) -> None:
            progress.update(
                f"{document.company} {document.call_date.isoformat()} "
                f"chunk {chunk_index + 1}/{chunk_total} ({len(chunk)} chars)"
            )

        retrieved_topics = retrieve_topics_from_chunks(
            retriever,
            chunks,
            request_delay_seconds=request_delay_seconds,
            slow_chunk_seconds=slow_chunk_seconds,
            chunk_start_callback=start_progress,
            progress_callback=advance_progress,
        )
        if max_topics_per_document is not None and max_topics_per_document > 0:
            if len(retrieved_topics) > max_topics_per_document:
                print(
                    f"\nWarning: limiting {document.company} {document.call_date.isoformat()} "
                    f"enrichment from {len(retrieved_topics)} to {max_topics_per_document} topics",
                    file=sys.stderr,
                )
            retrieved_topics = retrieved_topics[:max_topics_per_document]
        ensure_topic = (
            ontologist.ensure_topic
            if use_ontology_llm
            else lambda topic: assign_topic_without_llm(ontology, topic)
        )
        assignments = enrich_topics_with_progress(
            ensure_topic,
            retrieved_topics,
            document_label=f"{document.company} {document.call_date.isoformat()}",
            progress_update=progress.update,
            slow_enrichment_seconds=slow_enrichment_seconds,
        )
        progress.advance(f"{document.company} {document.call_date.isoformat()} enrichment complete")
        for assignment in assignments:
            observations.append(
                TopicObservation(
                    company=document.company,
                    call_date=document.call_date,
                    quarter=document.quarter,
                    topic_id=assignment.topic_id,
                    topic_name=assignment.topic_name,
                    mention_count=max(1, len(assignment.excerpts)),
                    excerpts=assignment.excerpts,
                )
            )
    progress.finish()

    excluded = {normalize_topic_name(topic) for topic in excluded_topic_list}
    filtered = [
        observation
        for observation in observations
        if normalize_topic_name(observation.topic_name) not in excluded
    ]

    trends = compute_trends(filtered, min_periods=min_periods, alpha=alpha)
    competitors = compute_competitor_analysis(filtered, top_n=top_n)

    return {
        "parameters": {
            "model": model,
            "provider": provider,
            "top_n": top_n,
            "alpha": alpha,
            "min_periods": min_periods,
            "excluded_topics": sorted(excluded_topic_list),
            "chunk_chars": chunk_chars,
            "request_delay_seconds": request_delay_seconds,
            "slow_chunk_seconds": slow_chunk_seconds,
            "slow_enrichment_seconds": slow_enrichment_seconds,
            "max_topics_per_document": max_topics_per_document,
            "use_ontology_llm": use_ontology_llm,
        },
        "documents": [
            {
                "company": document.company,
                "call_date": document.call_date.isoformat(),
                "quarter": document.quarter,
                "path": str(document.path),
            }
            for document in document_list
        ],
        "observations": [
            {
                "company": observation.company,
                "call_date": observation.call_date.isoformat(),
                "quarter": observation.quarter,
                "topic_id": observation.topic_id,
                "topic_name": observation.topic_name,
                "mention_count": observation.mention_count,
                "excerpts": observation.excerpts,
            }
            for observation in filtered
        ],
        "trend_analysis": trends,
        "competitor_analysis": competitors,
        "ontology": ontology.to_dict(),
    }


def retrieve_chunked_topics(
    retriever: TopicRetriever,
    document_text: str,
    *,
    chunk_chars: int = 6000,
    request_delay_seconds: float = 0.0,
    progress_callback: ProgressCallback | None = None,
    slow_chunk_seconds: float = 60.0,
) -> list[RetrievedTopic]:
    chunks = chunk_document_text(document_text, chunk_chars=chunk_chars)
    return retrieve_topics_from_chunks(
        retriever,
        chunks,
        request_delay_seconds=request_delay_seconds,
        progress_callback=progress_callback,
        slow_chunk_seconds=slow_chunk_seconds,
    )


def retrieve_topics_from_chunks(
    retriever: TopicRetriever,
    chunks: list[str],
    *,
    request_delay_seconds: float = 0.0,
    progress_callback: ProgressCallback | None = None,
    chunk_start_callback: ProgressCallback | None = None,
    slow_chunk_seconds: float = 60.0,
) -> list[RetrievedTopic]:
    merged: dict[str, RetrievedTopic] = {}
    for index, chunk in enumerate(chunks):
        if chunk_start_callback is not None:
            chunk_start_callback(chunk)
        started_at = time.monotonic()
        try:
            retrieved_topics = retriever.retrieve(chunk)
        except Exception as exc:
            print(
                f"\nWarning: skipped chunk {index + 1}/{len(chunks)} after LLM error: {exc}",
                file=sys.stderr,
            )
            retrieved_topics = []
        finally:
            elapsed = time.monotonic() - started_at
            if slow_chunk_seconds > 0 and elapsed >= slow_chunk_seconds:
                print(
                    f"\nWarning: chunk {index + 1}/{len(chunks)} took {elapsed:.1f}s "
                    f"({len(chunk)} chars)",
                    file=sys.stderr,
                )
            if progress_callback is not None:
                progress_callback(chunk)

        for topic in retrieved_topics:
            key = normalize_topic_name(topic.topic_name)
            existing = merged.get(key)
            if existing is None:
                merged[key] = topic
                continue
            excerpts = list(existing.excerpts)
            for excerpt in topic.excerpts:
                if excerpt not in excerpts:
                    excerpts.append(excerpt)
            merged[key] = RetrievedTopic(topic_name=existing.topic_name, excerpts=excerpts)
        if request_delay_seconds > 0 and index < len(chunks) - 1:
            time.sleep(request_delay_seconds)
    return sorted(merged.values(), key=lambda topic: normalize_topic_name(topic.topic_name))


def enrich_topics_with_progress(
    ensure_topic: Callable[[RetrievedTopic], OntologyAssignment],
    retrieved_topics: list[RetrievedTopic],
    *,
    document_label: str,
    progress_update: ProgressCallback | None = None,
    slow_enrichment_seconds: float = 60.0,
) -> list[OntologyAssignment]:
    assignments: list[OntologyAssignment] = []
    topic_total = len(retrieved_topics)
    for index, topic in enumerate(retrieved_topics, start=1):
        if progress_update is not None:
            progress_update(
                f"{document_label} enrichment {index}/{topic_total}: {topic.topic_name[:80]}"
            )
        started_at = time.monotonic()
        assignment = ensure_topic(topic)
        elapsed = time.monotonic() - started_at
        if slow_enrichment_seconds > 0 and elapsed >= slow_enrichment_seconds:
            print(
                f"\nWarning: enrichment topic {index}/{topic_total} took {elapsed:.1f}s: "
                f"{topic.topic_name}",
                file=sys.stderr,
            )
        assignments.append(assignment)
    return assignments


def assign_topic_without_llm(
    ontology: TopicsOntology,
    retrieved_topic: RetrievedTopic,
) -> OntologyAssignment:
    topic_id = ontology.find_topic_id(retrieved_topic.topic_name)
    existed = topic_id is not None
    if topic_id is None:
        topic_id = ontology.add_topic(retrieved_topic.topic_name)
    node = ontology.get_node(topic_id)
    return OntologyAssignment(
        topic_id=topic_id,
        topic_name=node.name,
        excerpts=retrieved_topic.excerpts,
        existed=existed,
        parent_topic_ids=ontology.parent_ids(topic_id),
    )


def chunk_document_text(document_text: str, *, chunk_chars: int = 6000) -> list[str]:
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")

    paragraphs = [paragraph.strip() for paragraph in document_text.splitlines() if paragraph.strip()]
    if not paragraphs:
        text = document_text.strip()
        return [text] if text else []

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for paragraph in paragraphs:
        if len(paragraph) > chunk_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_size = 0
            chunks.extend(split_long_paragraph(paragraph, chunk_chars))
            continue

        separator_size = 2 if current else 0
        next_size = current_size + separator_size + len(paragraph)
        if current and next_size > chunk_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_size = len(paragraph)
        else:
            current.append(paragraph)
            current_size = next_size

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def split_long_paragraph(paragraph: str, chunk_chars: int) -> list[str]:
    words = paragraph.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for word in words:
        separator_size = 1 if current else 0
        next_size = current_size + separator_size + len(word)
        if current and next_size > chunk_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_size = len(word)
        else:
            current.append(word)
            current_size = next_size
    if current:
        chunks.append(" ".join(current))
    return chunks


def compute_trends(
    observations: Iterable[TopicObservation],
    *,
    min_periods: int = 4,
    alpha: float = 0.05,
) -> dict[str, list[dict[str, object]]]:
    observations_by_company: dict[str, list[TopicObservation]] = defaultdict(list)
    for observation in observations:
        observations_by_company[observation.company].append(observation)

    output: dict[str, list[dict[str, object]]] = {}
    for company, company_observations in sorted(observations_by_company.items()):
        dates = sorted({observation.call_date for observation in company_observations})
        topic_names = {
            observation.topic_id: observation.topic_name for observation in company_observations
        }
        counts: dict[str, Counter[date]] = defaultdict(Counter)
        excerpts: dict[str, list[str]] = defaultdict(list)
        for observation in company_observations:
            counts[observation.topic_id][observation.call_date] += observation.mention_count
            excerpts[observation.topic_id].extend(observation.excerpts[:2])

        company_trends: list[dict[str, object]] = []
        for topic_id, per_date_counts in counts.items():
            series = [per_date_counts[call_date] for call_date in dates]
            active_periods = sum(1 for value in series if value > 0)
            if len(series) < min_periods or active_periods < 2:
                continue
            tau, p_value = kendall_tau_trend(series)
            if p_value > alpha or tau == 0:
                continue
            company_trends.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_names[topic_id],
                    "direction": "up" if tau > 0 else "down",
                    "kendall_tau": round(tau, 4),
                    "p_value": round(p_value, 6),
                    "series": [
                        {"call_date": call_date.isoformat(), "mention_count": count}
                        for call_date, count in zip(dates, series, strict=True)
                    ],
                    "sample_excerpts": excerpts[topic_id][:5],
                }
            )
        output[company] = sorted(
            company_trends,
            key=lambda item: (item["direction"], item["p_value"], -abs(float(item["kendall_tau"]))),
        )
    return output


def kendall_tau_trend(series: list[int]) -> tuple[float, float]:
    n = len(series)
    if n < 2:
        return 0.0, 1.0

    concordant = 0
    discordant = 0
    tied_y = 0
    for left in range(n - 1):
        for right in range(left + 1, n):
            diff = series[right] - series[left]
            if diff > 0:
                concordant += 1
            elif diff < 0:
                discordant += 1
            else:
                tied_y += 1

    total_pairs = n * (n - 1) / 2
    denominator = math.sqrt(total_pairs * (total_pairs - tied_y))
    if denominator == 0:
        return 0.0, 1.0

    tau = (concordant - discordant) / denominator
    variance = 2 * (2 * n + 5) / (9 * n * (n - 1))
    z_score = abs(tau) / math.sqrt(variance)
    p_value = math.erfc(z_score / math.sqrt(2))
    return tau, p_value


def compute_competitor_analysis(
    observations: Iterable[TopicObservation],
    *,
    top_n: int = 100,
) -> dict[str, object]:
    topic_counts: dict[str, Counter[str]] = defaultdict(Counter)
    topic_names: dict[str, str] = {}
    excerpts: dict[tuple[str, str], list[str]] = defaultdict(list)
    for observation in observations:
        topic_counts[observation.company][observation.topic_id] += observation.mention_count
        topic_names[observation.topic_id] = observation.topic_name
        excerpts[(observation.company, observation.topic_id)].extend(observation.excerpts[:2])

    top_topics: dict[str, set[str]] = {
        company: {topic_id for topic_id, _ in counts.most_common(top_n)}
        for company, counts in topic_counts.items()
    }
    companies = sorted(top_topics)

    matrix: dict[str, dict[str, float]] = {}
    common_topics: dict[str, list[dict[str, object]]] = {}
    unique_topics: dict[str, list[dict[str, object]]] = {}
    for company in companies:
        matrix[company] = {}
        peers = set().union(*(top_topics[peer] for peer in companies if peer != company))
        unique_topics[company] = [
            {
                "topic_id": topic_id,
                "topic_name": topic_names[topic_id],
                "mention_count": topic_counts[company][topic_id],
                "sample_excerpts": excerpts[(company, topic_id)][:3],
            }
            for topic_id in sorted(
                top_topics[company] - peers,
                key=lambda item: (-topic_counts[company][item], topic_names[item]),
            )
        ]
        for peer in companies:
            similarity = jaccard_similarity(top_topics[company], top_topics[peer])
            matrix[company][peer] = round(similarity, 4)
            if company < peer:
                shared = top_topics[company] & top_topics[peer]
                common_topics[f"{company}__{peer}"] = [
                    {
                        "topic_id": topic_id,
                        "topic_name": topic_names[topic_id],
                        "companies": {
                            company: {
                                "mention_count": topic_counts[company][topic_id],
                                "sample_excerpts": excerpts[(company, topic_id)][:2],
                            },
                            peer: {
                                "mention_count": topic_counts[peer][topic_id],
                                "sample_excerpts": excerpts[(peer, topic_id)][:2],
                            },
                        },
                    }
                    for topic_id in sorted(shared, key=lambda item: topic_names[item])
                ]

    return {
        "top_topics_by_company": {
            company: [
                {
                    "topic_id": topic_id,
                    "topic_name": topic_names[topic_id],
                    "mention_count": topic_counts[company][topic_id],
                }
                for topic_id, _ in topic_counts[company].most_common(top_n)
            ]
            for company in companies
        },
        "jaccard_similarity": matrix,
        "common_topics": common_topics,
        "unique_topics": unique_topics,
    }


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def load_exclude_topics(path: Path | None) -> list[str]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(topic, str) for topic in payload):
        raise ValueError("Exclude topics file must be a JSON array of strings")
    return payload


def main() -> None:
    load_dotenv_if_available()
    parser = argparse.ArgumentParser(
        description="Run Section 5.1 trend analysis and Section 5.2 competitor analysis on earnings calls."
    )
    parser.add_argument("--manifest", required=True, help="JSON manifest of call documents")
    parser.add_argument("--output", default="outputs/corpus_analysis.json", help="Output analysis JSON")
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
    parser.add_argument("--seed-topics", default="data/psb_seed_topics.json", help="Initial seed topics JSON")
    parser.add_argument("--exclude-topics", help="Optional JSON array of topic names to exclude")
    parser.add_argument("--top-n", type=int, default=100, help="Top topics per company for Jaccard analysis")
    parser.add_argument("--alpha", type=float, default=0.05, help="Trend significance cutoff")
    parser.add_argument("--min-periods", type=int, default=4, help="Minimum calls needed to test a trend")
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=6000,
        help="Maximum transcript characters per topic-extraction LLM request",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=0.0,
        help="Optional pause between chunk-level LLM requests to stay under provider TPM limits",
    )
    parser.add_argument(
        "--slow-chunk-seconds",
        type=float,
        default=60.0,
        help="Warn when a chunk-level LLM request takes at least this many seconds; use 0 to disable",
    )
    parser.add_argument(
        "--slow-enrichment-seconds",
        type=float,
        default=60.0,
        help="Warn when an ontology enrichment topic takes at least this many seconds; use 0 to disable",
    )
    parser.add_argument(
        "--max-topics-per-document",
        type=int,
        default=None,
        help="Optional cap on retrieved topics enriched per document to keep local LLM runs bounded",
    )
    parser.add_argument(
        "--ontology-mode",
        choices=["auto", "fast", "llm"],
        default=os.environ.get("CORPUS_ONTOLOGY_MODE", "auto"),
        help=(
            "How to enrich retrieved topics. auto uses fast exact-name enrichment for qwen "
            "and full LLM ontology enrichment for remote providers."
        ),
    )
    parser.add_argument(
        "--qwen-max-time-seconds",
        type=float,
        default=None,
        help="Optional per-generation time cap for --provider qwen; use 0 to disable",
    )
    parser.add_argument(
        "--qwen-max-new-tokens",
        type=int,
        default=None,
        help="Optional max new tokens per Qwen generation",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the corpus progress bar",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    documents = load_manifest(manifest_path)
    seed_topics = load_seed_topics(Path(args.seed_topics) if args.seed_topics else None)
    exclude_topics = load_exclude_topics(Path(args.exclude_topics) if args.exclude_topics else None)
    if args.qwen_max_time_seconds is not None:
        os.environ["TRANSFORMERS_GENERATION_MAX_TIME_SECONDS"] = str(args.qwen_max_time_seconds)
    if args.qwen_max_new_tokens is not None:
        os.environ["TRANSFORMERS_MAX_NEW_TOKENS"] = str(args.qwen_max_new_tokens)
    use_ontology_llm = args.ontology_mode == "llm" or (
        args.ontology_mode == "auto" and args.provider != "qwen"
    )

    analysis = run_corpus_analysis(
        documents,
        model=args.model,
        provider=args.provider,
        seed_topics=seed_topics,
        top_n=args.top_n,
        alpha=args.alpha,
        min_periods=args.min_periods,
        exclude_topics=exclude_topics,
        chunk_chars=args.chunk_chars,
        request_delay_seconds=args.request_delay_seconds,
        slow_chunk_seconds=args.slow_chunk_seconds,
        slow_enrichment_seconds=args.slow_enrichment_seconds,
        max_topics_per_document=args.max_topics_per_document,
        use_ontology_llm=use_ontology_llm,
        show_progress=not args.no_progress,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"Analyzed {len(documents)} earnings-call documents")
    print(f"Wrote corpus analysis to {output_path}")


if __name__ == "__main__":
    main()
