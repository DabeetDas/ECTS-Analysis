from __future__ import annotations


class ReWOOPlanner:
    """Static ReWOO-style planner: define evidence slots before workers execute."""

    def plan(self) -> list[str]:
        return [
            "E1: Parse uploaded investor presentation and earnings-call transcript.",
            "E2: Use Gemini to extract financial metrics into the data_new.xlsx-aligned schema.",
            "E3: Normalize units, metric names, periods, and validate FY25-only versus multi-year coverage.",
            "E4: Chunk transcript and retrieve metric-specific commentary using exact, adjacent, and keyword tools.",
            "E5: Link each extracted metric to ranked transcript evidence and numeric decomposition notes.",
            "E6: Use LLaMA-3.3-70B via Groq to synthesize grounded analyst insights.",
            "E7: Verify the output for unsupported claims, invented numbers, and invalid YoY language.",
        ]

