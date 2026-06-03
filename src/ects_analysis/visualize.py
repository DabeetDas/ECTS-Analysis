from __future__ import annotations

import argparse
import html
import json
import textwrap
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


NODE_WIDTH = 210
NODE_HEIGHT = 72
X_GAP = 95
Y_GAP = 34
MARGIN = 56

BANK_LABELS = {
    "BOB": "Bank of Baroda",
    "SBI": "State Bank of India",
    "PNB": "Punjab National Bank",
}


def load_ontology(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ontology = payload.get("ontology", payload)
    if not isinstance(ontology, dict):
        raise ValueError("Expected an ontology object or demo output with an `ontology` key")
    if not isinstance(ontology.get("nodes"), list) or not isinstance(ontology.get("edges"), list):
        raise ValueError("Ontology JSON must contain `nodes` and `edges` lists")
    return ontology


def load_visualization_data(path: Path) -> tuple[dict[str, Any], dict[str, list[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ontology = payload.get("ontology", payload)
    if not isinstance(ontology, dict):
        raise ValueError("Expected an ontology object or demo output with an `ontology` key")
    if not isinstance(ontology.get("nodes"), list) or not isinstance(ontology.get("edges"), list):
        raise ValueError("Ontology JSON must contain `nodes` and `edges` lists")
    return ontology, collect_assignment_excerpts(payload)


def load_corpus_analysis(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Corpus analysis JSON must be an object")
    required_keys = ["trend_analysis", "competitor_analysis", "observations"]
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Corpus analysis JSON is missing: {', '.join(missing)}")
    competitor_analysis = payload.get("competitor_analysis")
    if not isinstance(competitor_analysis, dict):
        raise ValueError("Corpus analysis `competitor_analysis` must be an object")
    return payload


def collect_assignment_excerpts(payload: dict[str, Any]) -> dict[str, list[str]]:
    excerpts_by_topic_id: dict[str, list[str]] = defaultdict(list)
    assignments = payload.get("assignments", [])
    if not isinstance(assignments, list):
        return excerpts_by_topic_id

    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue
        topic_id = assignment.get("topic_id")
        excerpts = assignment.get("excerpts", [])
        if not isinstance(topic_id, str) or not isinstance(excerpts, list):
            continue
        for excerpt in excerpts:
            if isinstance(excerpt, str) and excerpt not in excerpts_by_topic_id[topic_id]:
                excerpts_by_topic_id[topic_id].append(excerpt)
    return excerpts_by_topic_id


def render_corpus_html(payload: dict[str, Any], title: str = "PSB Corpus Analysis") -> str:
    documents = _list(payload.get("documents"))
    observations = _list(payload.get("observations"))
    trend_analysis = _dict(payload.get("trend_analysis"))
    competitor_analysis = _dict(payload.get("competitor_analysis"))
    parameters = _dict(payload.get("parameters"))
    matrix = _dict(competitor_analysis.get("jaccard_similarity"))
    top_topics = _dict(competitor_analysis.get("top_topics_by_company"))
    common_topics = _dict(competitor_analysis.get("common_topics"))
    unique_topics = _dict(competitor_analysis.get("unique_topics"))

    companies = sorted(
        {
            *[str(document.get("company")) for document in documents if isinstance(document, dict) and document.get("company")],
            *[str(company) for company in trend_analysis],
            *[str(company) for company in matrix],
            *[str(company) for company in top_topics],
        },
        key=bank_sort_key,
    )
    documents = sorted(documents, key=document_sort_key)
    observations = sorted(observations, key=observation_sort_key)
    topic_names = {
        str(observation.get("topic_name"))
        for observation in observations
        if isinstance(observation, dict) and observation.get("topic_name")
    }
    trending_up = sum(1 for trends in trend_analysis.values() for trend in _list(trends) if _dict(trend).get("direction") == "up")
    trending_down = sum(1 for trends in trend_analysis.values() for trend in _list(trends) if _dict(trend).get("direction") == "down")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f8;
      color: #17212b;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #f4f6f8;
      line-height: 1.45;
    }}
    .skip-link {{
      position: absolute;
      left: 16px;
      top: -48px;
      z-index: 10;
      border-radius: 6px;
      background: #123447;
      color: #ffffff;
      font-weight: 750;
      padding: 10px 12px;
      text-decoration: none;
    }}
    .skip-link:focus {{
      top: 12px;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 3;
      border-bottom: 1px solid #cfd7df;
      background: rgba(244, 246, 248, 0.97);
      backdrop-filter: blur(10px);
      padding: 18px 28px 16px;
    }}
    .eyebrow,
    .section-kicker {{
      margin: 0 0 5px;
      color: #526474;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0;
      color: #111923;
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 0;
    }}
    .lede {{
      max-width: 900px;
      margin: 7px 0 0;
      color: #405365;
      font-size: 14px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    nav a {{
      border: 1px solid #bdc8d2;
      border-radius: 6px;
      color: #203443;
      font-size: 13px;
      font-weight: 650;
      padding: 7px 10px;
      text-decoration: none;
      background: #ffffff;
    }}
    nav a:hover,
    nav a:focus-visible {{
      border-color: #1f6f8b;
      color: #123447;
      outline: 2px solid #8fc6d8;
      outline-offset: 2px;
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 28px 52px;
    }}
    main:focus {{
      outline: none;
    }}
    section {{
      border-top: 1px solid #cfd7df;
      padding: 26px 0 10px;
    }}
    section:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    h2 {{
      margin: 0;
      color: #111923;
      font-size: 19px;
      font-weight: 800;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 20px 0 10px;
      color: #243747;
      font-size: 14px;
      font-weight: 750;
      letter-spacing: 0;
    }}
    .section-heading {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }}
    .metric {{
      border: 1px solid #d1d9e1;
      border-radius: 6px;
      background: #ffffff;
      padding: 14px;
    }}
    .metric-label {{
      color: #526474;
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
    }}
    .metric-value {{
      margin-top: 6px;
      color: #111923;
      font-size: 24px;
      font-weight: 820;
    }}
    .insight-panel {{
      border: 1px solid #d1d9e1;
      border-radius: 6px;
      background: #ffffff;
      margin-top: 14px;
      padding: 14px 16px;
    }}
    .insight-panel h3 {{
      margin-top: 0;
    }}
    .insight-list {{
      margin: 0;
      padding-left: 18px;
      color: #243747;
    }}
    .insight-list li {{
      margin: 0 0 7px;
    }}
    .table-wrap {{
      width: 100%;
      overflow-x: auto;
      border: 1px solid #d1d9e1;
      border-radius: 6px;
      background: #ffffff;
    }}
    table {{
      width: 100%;
      min-width: 720px;
      border-collapse: collapse;
      font-size: 13px;
    }}
    caption {{
      text-align: left;
      color: #405365;
      font-size: 12px;
      font-weight: 650;
      padding: 10px 10px 0;
    }}
    th, td {{
      border-bottom: 1px solid #e3e8ed;
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #e9eef2;
      color: #243747;
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
    }}
    tbody tr:nth-child(even) {{
      background: #fbfcfd;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .matrix th:first-child {{
      left: 0;
      z-index: 1;
    }}
    .matrix td:first-child {{
      position: sticky;
      left: 0;
      background: #ffffff;
      font-weight: 750;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 750;
      padding: 3px 8px;
      white-space: nowrap;
    }}
    .pill-up {{
      background: #dcefe8;
      color: #0f4a3f;
    }}
    .pill-down {{
      background: #f3ded8;
      color: #7a321f;
    }}
    .excerpt-list {{
      margin: 0;
      padding-left: 17px;
      color: #40505c;
    }}
    .excerpt-list li {{
      margin: 0 0 5px;
    }}
    details {{
      border: 1px solid #d1d9e1;
      border-radius: 6px;
      background: #ffffff;
      margin: 10px 0;
    }}
    summary {{
      cursor: pointer;
      font-size: 14px;
      font-weight: 750;
      padding: 11px 12px;
    }}
    summary:focus-visible {{
      outline: 2px solid #8fc6d8;
      outline-offset: 2px;
    }}
    details > .details-body {{
      border-top: 1px solid #e3e8ed;
      padding: 12px;
    }}
    .empty {{
      border: 1px dashed #bdc8d2;
      border-radius: 6px;
      color: #526474;
      background: #ffffff;
      padding: 14px;
      font-size: 13px;
    }}
    .small {{
      color: #526474;
      font-size: 12px;
    }}
    .bank-name {{
      font-weight: 780;
      color: #111923;
    }}
    .bank-code {{
      color: #526474;
      font-size: 12px;
      font-weight: 650;
    }}
    @media (max-width: 720px) {{
      header, main {{
        padding-left: 14px;
        padding-right: 14px;
      }}
      h1 {{
        font-size: 19px;
      }}
      table {{
        min-width: 640px;
      }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <header>
    <div class="eyebrow">Public Sector Bank Earnings Call Intelligence</div>
    <h1>{html.escape(title)}</h1>
    <p class="lede">Bank-sorted topic, trend, and peer comparison dashboard generated from the latest corpus analysis output.</p>
    <nav aria-label="Dashboard sections">
      <a href="#summary">Summary</a>
      <a href="#bank-overview">Bank Overview</a>
      <a href="#trends">Trends</a>
      <a href="#competitors">Competitors</a>
      <a href="#common">Common Topics</a>
      <a href="#unique">Unique Topics</a>
      <a href="#top">Top Topics</a>
      <a href="#observations">Observations</a>
    </nav>
  </header>
  <main id="main" tabindex="-1">
    <section id="summary">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Executive Snapshot</p>
          <h2>Summary</h2>
        </div>
      </div>
      <div class="metric-grid">
        {render_metric("Companies", len(companies))}
        {render_metric("Documents", len(documents))}
        {render_metric("Topic Observations", len(observations))}
        {render_metric("Unique Topics", len(topic_names))}
        {render_metric("Trending Up", trending_up)}
        {render_metric("Trending Down", trending_down)}
      </div>
      {render_executive_notes(companies, observations, matrix, top_topics, trending_up, trending_down)}
      {render_parameters(parameters)}
      {render_documents_table(documents)}
    </section>
    <section id="bank-overview">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Bank Sorted View</p>
          <h2>Bank Overview</h2>
        </div>
      </div>
      {render_bank_overview(companies, documents, observations, trend_analysis, top_topics)}
    </section>
    <section id="trends">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Movement Across Calls</p>
          <h2>Trend Analysis</h2>
        </div>
      </div>
      {render_trends(trend_analysis, companies)}
    </section>
    <section id="competitors">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Peer Similarity</p>
          <h2>Competitor Analysis</h2>
        </div>
      </div>
      {render_jaccard_matrix(matrix, companies)}
    </section>
    <section id="common">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Shared Strategic Themes</p>
          <h2>Common Topics Between Banks</h2>
        </div>
      </div>
      {render_common_topics(common_topics, companies)}
    </section>
    <section id="unique">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Differentiated Emphasis</p>
          <h2>Unique Topics By Bank</h2>
        </div>
      </div>
      {render_unique_topics(unique_topics, companies)}
    </section>
    <section id="top">
      <div class="section-heading">
        <div>
          <p class="section-kicker">Highest Mention Counts</p>
          <h2>Top Topics By Bank</h2>
        </div>
      </div>
      {render_top_topics(top_topics, companies)}
    </section>
    <section id="observations">
      <h2>Raw Topic Observations</h2>
      {render_observations_table(observations)}
    </section>
  </main>
</body>
</html>
"""


def bank_sort_key(value: str) -> tuple[str, str]:
    code = str(value)
    return (BANK_LABELS.get(code, code).casefold(), code.casefold())


def format_bank_name(value: str) -> str:
    code = str(value)
    label = BANK_LABELS.get(code)
    return f"{label} ({code})" if label else code


def render_bank_name(value: str) -> str:
    code = str(value)
    label = BANK_LABELS.get(code)
    if not label:
        return f'<span class="bank-name">{html.escape(code)}</span>'
    return (
        f'<span class="bank-name">{html.escape(label)}</span> '
        f'<span class="bank-code">({html.escape(code)})</span>'
    )


def ordered_companies(section: dict[str, Any], companies: list[str]) -> list[str]:
    seen = set(companies)
    extra = [company for company in section if company not in seen]
    return [company for company in companies if company in section] + sorted(extra, key=bank_sort_key)


def document_sort_key(value: Any) -> tuple[str, str, str]:
    item = _dict(value)
    return (
        bank_sort_key(str(item.get("company", "")))[0],
        str(item.get("call_date", "")),
        str(item.get("quarter", "")),
    )


def observation_sort_key(value: Any) -> tuple[str, str, str]:
    item = _dict(value)
    return (
        bank_sort_key(str(item.get("company", "")))[0],
        str(item.get("call_date", "")),
        str(item.get("topic_name", "")),
    )


def split_pair_key(pair_key: str) -> list[str]:
    return [part for part in pair_key.split("__") if part]


def pair_sort_key(pair_key: str, companies: list[str]) -> tuple[int, int, str]:
    order = {company: index for index, company in enumerate(companies)}
    pair = split_pair_key(pair_key)
    first = order.get(pair[0], len(order)) if pair else len(order)
    second = order.get(pair[1], len(order)) if len(pair) > 1 else len(order)
    return (first, second, pair_key.casefold())


def render_metric(label: str, value: object) -> str:
    return f"""
        <div class="metric">
          <div class="metric-label">{html.escape(label)}</div>
          <div class="metric-value">{html.escape(str(value))}</div>
        </div>"""


def render_executive_notes(
    companies: list[str],
    observations: list[Any],
    matrix: dict[str, Any],
    top_topics: dict[str, Any],
    trending_up: int,
    trending_down: int,
) -> str:
    notes = []
    if companies:
        observation_counts = Counter(
            str(_dict(observation).get("company", ""))
            for observation in observations
            if _dict(observation).get("company")
        )
        if observation_counts:
            company, count = max(observation_counts.items(), key=lambda item: (item[1], bank_sort_key(item[0])))
            notes.append(
                f"{format_bank_name(company)} has the broadest extracted topic coverage with {count} topic observations."
            )

    strongest_pair = strongest_similarity_pair(matrix, companies)
    if strongest_pair is not None:
        left, right, score = strongest_pair
        notes.append(
            f"The strongest peer-topic overlap is {format_bank_name(left)} vs {format_bank_name(right)} at {score:.4f}."
        )

    for company in companies[:3]:
        topics = _list(top_topics.get(company))
        if topics:
            top_topic = _dict(topics[0])
            notes.append(
                f"{format_bank_name(company)} most frequently emphasizes {top_topic.get('topic_name', 'N/A')}."
            )

    notes.append(
        f"Trend testing returned {trending_up} upward and {trending_down} downward significant topic movements."
    )

    rows = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
    return f"""
      <div class="insight-panel" aria-labelledby="analyst-read-heading">
        <h3 id="analyst-read-heading">Analyst Read</h3>
        <ul class="insight-list">{rows}</ul>
      </div>"""


def render_bank_overview(
    companies: list[str],
    documents: list[Any],
    observations: list[Any],
    trend_analysis: dict[str, Any],
    top_topics: dict[str, Any],
) -> str:
    if not companies:
        return '<div class="empty">No bank-level data found in this output.</div>'

    rows = []
    for company in companies:
        company_documents = [_dict(document) for document in documents if _dict(document).get("company") == company]
        company_observations = [
            _dict(observation) for observation in observations if _dict(observation).get("company") == company
        ]
        latest_call = max((str(document.get("call_date", "")) for document in company_documents), default="")
        unique_topics = {
            str(observation.get("topic_name"))
            for observation in company_observations
            if observation.get("topic_name")
        }
        trends = _list(trend_analysis.get(company))
        top_topic_items = _list(top_topics.get(company))
        top_topic = _dict(top_topic_items[0]).get("topic_name", "") if top_topic_items else ""
        rows.append(
            "<tr>"
            f"<th scope=\"row\">{render_bank_name(company)}</th>"
            f"<td class=\"num\">{len(company_documents)}</td>"
            f"<td>{html.escape(latest_call)}</td>"
            f"<td class=\"num\">{len(unique_topics)}</td>"
            f"<td class=\"num\">{len(trends)}</td>"
            f"<td>{html.escape(str(top_topic) if top_topic else 'No top topic')}</td>"
            "</tr>"
        )

    return f"""
      <div class="table-wrap">
        <table>
          <caption>Bank-level summary sorted by bank name.</caption>
          <thead><tr><th scope="col">Bank</th><th scope="col" class="num">Documents</th><th scope="col">Latest Call</th><th scope="col" class="num">Observed Topics</th><th scope="col" class="num">Significant Trends</th><th scope="col">Top Topic</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


def render_parameters(parameters: dict[str, Any]) -> str:
    if not parameters:
        return ""
    rows = []
    for key, value in sorted(parameters.items()):
        display_value = ", ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        rows.append(
            f"<tr><td>{html.escape(pretty_label(key))}</td><td>{html.escape(display_value)}</td></tr>"
        )
    return f"""
      <h3>Parameters</h3>
      <div class="table-wrap">
        <table>
          <caption>Model and analysis settings used to produce this report.</caption>
          <thead><tr><th scope="col">Parameter</th><th scope="col">Value</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


def render_documents_table(documents: list[Any]) -> str:
    if not documents:
        return ""
    rows = []
    for document in documents:
        item = _dict(document)
        rows.append(
            "<tr>"
            f"<th scope=\"row\">{render_bank_name(str(item.get('company', '')))}</th>"
            f"<td>{html.escape(str(item.get('quarter', '') or ''))}</td>"
            f"<td>{html.escape(str(item.get('call_date', '')))}</td>"
            f"<td>{html.escape(str(item.get('path', '')))}</td>"
            "</tr>"
        )
    return f"""
      <h3>Documents</h3>
      <div class="table-wrap">
        <table>
          <caption>Source transcripts sorted by bank and call date.</caption>
          <thead><tr><th scope="col">Bank</th><th scope="col">Quarter</th><th scope="col">Call Date</th><th scope="col">Path</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


def render_trends(trend_analysis: dict[str, Any], companies: list[str]) -> str:
    if not trend_analysis:
        return '<div class="empty">No significant trends found in this output.</div>'
    chunks = []
    for company in ordered_companies(trend_analysis, companies):
        trends = _list(trend_analysis.get(company))
        if not trends:
            chunks.append(f"<details><summary>{render_bank_name(company)}: no significant trends</summary><div class=\"details-body small\">No topics passed the configured Kendall tau threshold.</div></details>")
            continue
        rows = []
        for trend in trends:
            item = _dict(trend)
            direction = str(item.get("direction", ""))
            pill_class = "pill-up" if direction == "up" else "pill-down"
            rows.append(
                "<tr>"
                f"<th scope=\"row\">{html.escape(str(item.get('topic_name', '')))}</th>"
                f"<td><span class=\"pill {pill_class}\">{html.escape(direction.title())}</span></td>"
                f"<td class=\"num\">{html.escape(str(item.get('kendall_tau', '')))}</td>"
                f"<td class=\"num\">{html.escape(str(item.get('p_value', '')))}</td>"
                f"<td>{render_series(item.get('series'))}</td>"
                f"<td>{render_excerpt_list(item.get('sample_excerpts'), limit=3)}</td>"
                "</tr>"
            )
        chunks.append(f"""
        <details open>
          <summary>{render_bank_name(company)}: {len(trends)} significant trend{'s' if len(trends) != 1 else ''}</summary>
          <div class="details-body">
            <div class="table-wrap">
              <table>
                <caption>Significant topic movement for {html.escape(format_bank_name(company))}.</caption>
                <thead><tr><th scope="col">Topic</th><th scope="col">Direction</th><th scope="col" class="num">Kendall Tau</th><th scope="col" class="num">P Value</th><th scope="col">Series</th><th scope="col">Sample Excerpts</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </div>
          </div>
        </details>""")
    return "\n".join(chunks)


def render_jaccard_matrix(matrix: dict[str, Any], companies: list[str]) -> str:
    if not matrix or not companies:
        return '<div class="empty">No competitor similarity matrix found in this output.</div>'
    header = "".join(f"<th scope=\"col\">{render_bank_name(company)}</th>" for company in companies)
    rows = []
    for company in companies:
        company_scores = _dict(matrix.get(company))
        cells = []
        for peer in companies:
            value = parse_float(company_scores.get(peer), default=0.0)
            cells.append(
                f'<td class="num" style="background: {similarity_color(value)}">{value:.4f}</td>'
            )
        rows.append(f"<tr><th scope=\"row\">{render_bank_name(company)}</th>{''.join(cells)}</tr>")
    return f"""
      <div class="table-wrap">
        <table class="matrix">
          <caption>Topic overlap between banks based on top-topic Jaccard similarity.</caption>
          <thead><tr><th scope="col">Bank</th>{header}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      <p class="small">Higher values mean stronger overlap between each bank's top topics.</p>"""


def render_common_topics(common_topics: dict[str, Any], companies: list[str]) -> str:
    if not common_topics:
        return '<div class="empty">No common-topic pairs found in this output.</div>'
    chunks = []
    for pair_key in sorted(common_topics, key=lambda key: pair_sort_key(key, companies)):
        topics = _list(common_topics.get(pair_key))
        rows = []
        for topic in topics:
            item = _dict(topic)
            companies = _dict(item.get("companies"))
            company_cells = []
            for company in sorted(companies, key=bank_sort_key):
                details = _dict(companies.get(company))
                count = details.get("mention_count", 0)
                company_cells.append(
                    f"<strong>{html.escape(format_bank_name(company))}</strong>: {html.escape(str(count))}"
                    f"{render_excerpt_list(details.get('sample_excerpts'), limit=2)}"
                )
            rows.append(
                "<tr>"
                f"<th scope=\"row\">{html.escape(str(item.get('topic_name', '')))}</th>"
                f"<td>{''.join(company_cells)}</td>"
                "</tr>"
            )
        label = " and ".join(format_bank_name(company) for company in split_pair_key(pair_key))
        chunks.append(f"""
        <details>
          <summary>{html.escape(label)}: {len(topics)} shared topic{'s' if len(topics) != 1 else ''}</summary>
          <div class="details-body">
            <div class="table-wrap">
              <table>
                <caption>Shared topics for {html.escape(label)}.</caption>
                <thead><tr><th scope="col">Topic</th><th scope="col">Mentions And Excerpts</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </div>
          </div>
        </details>""")
    return "\n".join(chunks)


def render_unique_topics(unique_topics: dict[str, Any], companies: list[str]) -> str:
    if not unique_topics:
        return '<div class="empty">No unique topics found in this output.</div>'
    chunks = []
    for company in ordered_companies(unique_topics, companies):
        topics = _list(unique_topics.get(company))
        rows = []
        for topic in topics:
            item = _dict(topic)
            rows.append(
                "<tr>"
                f"<th scope=\"row\">{html.escape(str(item.get('topic_name', '')))}</th>"
                f"<td class=\"num\">{html.escape(str(item.get('mention_count', '')))}</td>"
                f"<td>{render_excerpt_list(item.get('sample_excerpts'), limit=3)}</td>"
                "</tr>"
            )
        chunks.append(f"""
        <details>
          <summary>{render_bank_name(company)}: {len(topics)} unique topic{'s' if len(topics) != 1 else ''}</summary>
          <div class="details-body">
            {render_topic_rows(rows, f"Unique topics for {format_bank_name(company)}.")}
          </div>
        </details>""")
    return "\n".join(chunks)


def render_top_topics(top_topics: dict[str, Any], companies: list[str]) -> str:
    if not top_topics:
        return '<div class="empty">No top-topic data found in this output.</div>'
    chunks = []
    for company in ordered_companies(top_topics, companies):
        topics = _list(top_topics.get(company))
        rows = []
        for topic in topics:
            item = _dict(topic)
            rows.append(
                "<tr>"
                f"<th scope=\"row\">{html.escape(str(item.get('topic_name', '')))}</th>"
                f"<td class=\"num\">{html.escape(str(item.get('mention_count', '')))}</td>"
                "</tr>"
            )
        chunks.append(f"""
        <details>
          <summary>{render_bank_name(company)}: top {len(topics)} topic{'s' if len(topics) != 1 else ''}</summary>
          <div class="details-body">
            <div class="table-wrap">
              <table>
                <caption>Highest-frequency topics for {html.escape(format_bank_name(company))}.</caption>
                <thead><tr><th scope="col">Topic</th><th scope="col" class="num">Mentions</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </div>
          </div>
        </details>""")
    return "\n".join(chunks)


def render_observations_table(observations: list[Any]) -> str:
    if not observations:
        return '<div class="empty">No raw topic observations found in this output.</div>'
    rows = []
    for observation in observations:
        item = _dict(observation)
        rows.append(
            "<tr>"
            f"<th scope=\"row\">{render_bank_name(str(item.get('company', '')))}</th>"
            f"<td>{html.escape(str(item.get('quarter', '') or ''))}</td>"
            f"<td>{html.escape(str(item.get('call_date', '')))}</td>"
            f"<td>{html.escape(str(item.get('topic_name', '')))}</td>"
            f"<td class=\"num\">{html.escape(str(item.get('mention_count', '')))}</td>"
            f"<td>{render_excerpt_list(item.get('excerpts'), limit=4)}</td>"
            "</tr>"
        )
    return f"""
      <div class="table-wrap">
        <table>
          <caption>Detailed topic observations sorted by bank, date, and topic.</caption>
          <thead><tr><th scope="col">Bank</th><th scope="col">Quarter</th><th scope="col">Date</th><th scope="col">Topic</th><th scope="col" class="num">Mentions</th><th scope="col">Excerpts</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


def render_topic_rows(rows: list[str], caption: str) -> str:
    if not rows:
        return '<div class="empty">No topics in this section.</div>'
    return f"""
            <div class="table-wrap">
              <table>
                <caption>{html.escape(caption)}</caption>
                <thead><tr><th scope="col">Topic</th><th scope="col" class="num">Mentions</th><th scope="col">Sample Excerpts</th></tr></thead>
                <tbody>{''.join(rows)}</tbody>
              </table>
            </div>"""


def render_series(value: Any) -> str:
    series = _list(value)
    if not series:
        return ""
    parts = []
    for item in series:
        point = _dict(item)
        parts.append(f"{point.get('call_date', '')}: {point.get('mention_count', '')}")
    return html.escape("; ".join(parts))


def render_excerpt_list(value: Any, limit: int) -> str:
    excerpts = [str(item) for item in _list(value) if item]
    if not excerpts:
        return '<span class="small">(none)</span>'
    rows = [f"<li>{html.escape(excerpt)}</li>" for excerpt in excerpts[:limit]]
    if len(excerpts) > limit:
        rows.append(f'<li class="small">... {len(excerpts) - limit} more</li>')
    return f'<ul class="excerpt-list">{"".join(rows)}</ul>'


def similarity_color(value: float) -> str:
    clamped = min(max(value, 0.0), 1.0)
    red = round(255 - clamped * 84)
    green = round(255 - clamped * 55)
    blue = round(255 - clamped * 96)
    return f"rgb({red}, {green}, {blue})"


def strongest_similarity_pair(
    matrix: dict[str, Any],
    companies: list[str],
) -> tuple[str, str, float] | None:
    best: tuple[str, str, float] | None = None
    for left_index, left in enumerate(companies):
        left_scores = _dict(matrix.get(left))
        for right in companies[left_index + 1 :]:
            score = parse_float(left_scores.get(right), default=0.0)
            if best is None or score > best[2]:
                best = (left, right, score)
    return best


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pretty_label(value: str) -> str:
    return value.replace("_", " ").title()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def render_ontology_html(
    ontology: dict[str, Any],
    title: str = "Topics Ontology",
    excerpts_by_topic_id: dict[str, list[str]] | None = None,
) -> str:
    excerpts_by_topic_id = excerpts_by_topic_id or {}
    nodes = {node["topic_id"]: node for node in ontology["nodes"]}
    edges = ontology["edges"]
    children: dict[str, set[str]] = defaultdict(set)
    parents: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        parent_id = edge["parent_id"]
        child_id = edge["child_id"]
        if parent_id in nodes and child_id in nodes:
            children[parent_id].add(child_id)
            parents[child_id].add(parent_id)

    layers = compute_layers(nodes, children, parents)
    positions, width, height = compute_positions(layers, children)
    edge_markup = "\n".join(render_edge(edge, positions) for edge in edges if edge["parent_id"] in positions and edge["child_id"] in positions)
    node_markup = "\n".join(
        render_node(
            nodes[node_id],
            positions[node_id],
            parents[node_id],
            children[node_id],
            nodes,
            excerpts_by_topic_id.get(node_id, []),
            width,
            height,
        )
        for node_id in sorted(positions, key=lambda item: (positions[item][0], positions[item][1]))
    )

    node_count = len(nodes)
    edge_count = len(edges)
    root_count = len([node_id for node_id in nodes if not parents[node_id]])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f7f4;
      color: #1f2933;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #f7f7f4;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 2;
      border-bottom: 1px solid #d8ded8;
      background: rgba(247, 247, 244, 0.94);
      backdrop-filter: blur(10px);
      padding: 18px 24px 14px;
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 10px;
      color: #50606b;
      font-size: 13px;
    }}
    main {{
      overflow: auto;
      padding: 22px;
    }}
    svg {{
      display: block;
      min-width: 100%;
      background: #ffffff;
      border: 1px solid #d8ded8;
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(31, 41, 51, 0.08);
    }}
    .edge {{
      fill: none;
      stroke: #8a979f;
      stroke-width: 1.4;
      opacity: 0.72;
    }}
    .node rect {{
      fill: #ffffff;
      stroke: #2f6f5e;
      stroke-width: 1.4;
      rx: 8;
    }}
    .node.multi-parent rect {{
      stroke: #b6543c;
      stroke-width: 2;
    }}
    .node.root rect {{
      fill: #edf7f2;
    }}
    .node:hover rect {{
      fill: #fff8e8;
      stroke-width: 2.4;
    }}
    .node:hover text {{
      fill: #0f1d25;
    }}
    .hover-panel {{
      display: none;
      pointer-events: none;
    }}
    .node:hover .hover-panel {{
      display: block;
    }}
    .hover-panel-box {{
      background: #fffdf7;
      border: 1px solid #c6d1ca;
      border-radius: 8px;
      box-shadow: 0 14px 36px rgba(31, 41, 51, 0.18);
      color: #1f2933;
      font-size: 12px;
      line-height: 1.35;
      max-height: 260px;
      overflow: hidden;
      padding: 12px;
    }}
    .hover-panel-title {{
      color: #132027;
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .hover-panel-label {{
      color: #53616a;
      font-weight: 700;
      margin-top: 7px;
    }}
    .hover-panel-text {{
      color: #27343c;
      margin-top: 3px;
    }}
    .node-title {{
      fill: #18242c;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .node-detail {{
      fill: #66747d;
      font-size: 11px;
      letter-spacing: 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">
      <span>{node_count} topics</span>
      <span>{edge_count} relationships</span>
      <span>{root_count} root topics</span>
      <span>hover a topic to read parents and excerpts</span>
      <span>orange outline = multiple parents</span>
    </div>
  </header>
  <main>
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)} DAG visualization">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#8a979f"></path>
        </marker>
      </defs>
      <g class="edges">
{edge_markup}
      </g>
      <g class="nodes">
{node_markup}
      </g>
    </svg>
  </main>
</body>
</html>
"""


def compute_layers(
    nodes: dict[str, dict[str, Any]],
    children: dict[str, set[str]],
    parents: dict[str, set[str]],
) -> list[list[str]]:
    indegree = {node_id: len(parents[node_id]) for node_id in nodes}
    queue = deque(sorted([node_id for node_id, count in indegree.items() if count == 0], key=lambda item: nodes[item]["name"]))
    depth = {node_id: 0 for node_id in queue}

    while queue:
        current = queue.popleft()
        for child_id in sorted(children[current], key=lambda item: nodes[item]["name"]):
            depth[child_id] = max(depth.get(child_id, 0), depth[current] + 1)
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)

    for node_id in nodes:
        depth.setdefault(node_id, 0)

    grouped: dict[int, list[str]] = defaultdict(list)
    for node_id, layer in depth.items():
        grouped[layer].append(node_id)

    layers: list[list[str]] = []
    previous_order: dict[str, int] = {}
    for layer in range(max(grouped) + 1):
        layer_nodes = grouped[layer]
        if layer == 0:
            ordered = sorted(layer_nodes, key=lambda item: nodes[item]["name"])
        else:
            ordered = sorted(
                layer_nodes,
                key=lambda item: (
                    parent_barycenter(item, parents, previous_order),
                    nodes[item]["name"],
                ),
            )
        layers.append(ordered)
        previous_order = {node_id: index for index, node_id in enumerate(ordered)}
    return layers


def parent_barycenter(
    node_id: str,
    parents: dict[str, set[str]],
    previous_order: dict[str, int],
) -> float:
    parent_positions = [
        previous_order[parent_id]
        for parent_id in parents[node_id]
        if parent_id in previous_order
    ]
    if not parent_positions:
        return float("inf")
    return sum(parent_positions) / len(parent_positions)


def compute_positions(
    layers: list[list[str]],
    children: dict[str, set[str]],
) -> tuple[dict[str, tuple[int, int]], int, int]:
    max_layer_size = max((len(layer) for layer in layers), default=1)
    width = MARGIN * 2 + len(layers) * NODE_WIDTH + max(len(layers) - 1, 0) * X_GAP
    height = MARGIN * 2 + max_layer_size * NODE_HEIGHT + max(max_layer_size - 1, 0) * Y_GAP
    positions: dict[str, tuple[int, int]] = {}

    for layer_index in range(len(layers) - 1, -1, -1):
        layer = layers[layer_index]
        x = MARGIN + layer_index * (NODE_WIDTH + X_GAP)
        desired_positions: list[tuple[float, str]] = []
        for fallback_index, node_id in enumerate(layer):
            child_centers = [
                positions[child_id][1] + NODE_HEIGHT / 2
                for child_id in children[node_id]
                if child_id in positions
            ]
            if child_centers:
                desired_y = sum(child_centers) / len(child_centers) - NODE_HEIGHT / 2
            else:
                desired_y = MARGIN + fallback_index * (NODE_HEIGHT + Y_GAP)
            desired_positions.append((desired_y, node_id))

        for node_id, y in pack_column(desired_positions):
            positions[node_id] = (x, y)

    return positions, width, height


def pack_column(desired_positions: list[tuple[float, str]]) -> list[tuple[str, int]]:
    packed: list[tuple[str, int]] = []
    min_y = MARGIN
    for desired_y, node_id in sorted(desired_positions):
        y = max(int(round(desired_y)), min_y)
        packed.append((node_id, y))
        min_y = y + NODE_HEIGHT + Y_GAP
    return packed


def render_edge(edge: dict[str, Any], positions: dict[str, tuple[int, int]]) -> str:
    parent_x, parent_y = positions[edge["parent_id"]]
    child_x, child_y = positions[edge["child_id"]]
    start_x = parent_x + NODE_WIDTH
    start_y = parent_y + NODE_HEIGHT // 2
    end_x = child_x
    end_y = child_y + NODE_HEIGHT // 2
    mid_x = start_x + max((end_x - start_x) // 2, 34)
    path = f"M {start_x} {start_y} C {mid_x} {start_y}, {mid_x} {end_y}, {end_x - 8} {end_y}"
    return f'        <path class="edge" d="{path}" marker-end="url(#arrow)"></path>'


def render_node(
    node: dict[str, Any],
    position: tuple[int, int],
    parent_ids: set[str],
    child_ids: set[str],
    nodes: dict[str, dict[str, Any]],
    excerpts: list[str],
    canvas_width: int,
    canvas_height: int,
) -> str:
    x, y = position
    aliases = node.get("aliases") or []
    classes = ["node"]
    if not parent_ids:
        classes.append("root")
    if len(parent_ids) > 1:
        classes.append("multi-parent")

    detail = f"{len(parent_ids)} parent{'s' if len(parent_ids) != 1 else ''}"
    if aliases:
        detail += f" | aliases: {', '.join(aliases[:2])}"
        if len(aliases) > 2:
            detail += f" +{len(aliases) - 2}"
    if excerpts:
        detail += f" | {len(excerpts)} excerpt{'s' if len(excerpts) != 1 else ''}"

    title_lines = wrap_label(node["name"], 24, 2)
    detail_lines = wrap_label(detail, 32, 1)
    tooltip = build_node_tooltip(node, parent_ids, child_ids, nodes, excerpts)
    hover_panel = render_hover_panel(
        node=node,
        position=position,
        parent_ids=parent_ids,
        child_ids=child_ids,
        nodes=nodes,
        excerpts=excerpts,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )
    text_lines = []
    for index, line in enumerate(title_lines):
        text_lines.append(
            f'          <text class="node-title" x="{x + 14}" y="{y + 24 + index * 15}">{html.escape(line)}</text>'
        )
    detail_y = y + 58
    for index, line in enumerate(detail_lines):
        text_lines.append(
            f'          <text class="node-detail" x="{x + 14}" y="{detail_y + index * 13}">{html.escape(line)}</text>'
        )

    return "\n".join(
        [
            f'        <g class="{" ".join(classes)}">',
            f"          <title>{html.escape(tooltip)}</title>",
            f'          <rect x="{x}" y="{y}" width="{NODE_WIDTH}" height="{NODE_HEIGHT}"></rect>',
            *text_lines,
            hover_panel,
            "        </g>",
        ]
    )


def render_hover_panel(
    node: dict[str, Any],
    position: tuple[int, int],
    parent_ids: set[str],
    child_ids: set[str],
    nodes: dict[str, dict[str, Any]],
    excerpts: list[str],
    canvas_width: int,
    canvas_height: int,
) -> str:
    x, y = position
    panel_width = 380
    panel_height = 260
    panel_x = x + NODE_WIDTH + 14
    if panel_x + panel_width > canvas_width - MARGIN:
        panel_x = max(MARGIN, x - panel_width - 14)
    panel_y = min(max(MARGIN, y - 18), max(MARGIN, canvas_height - panel_height - MARGIN))

    parent_names = sorted(nodes[parent_id]["name"] for parent_id in parent_ids if parent_id in nodes)
    child_names = sorted(nodes[child_id]["name"] for child_id in child_ids if child_id in nodes)
    aliases = node.get("aliases") or []
    excerpts_html = "".join(
        f'<div class="hover-panel-text">- {html.escape(excerpt)}</div>'
        for excerpt in excerpts[:4]
    )
    if len(excerpts) > 4:
        excerpts_html += f'<div class="hover-panel-text">- ... {len(excerpts) - 4} more</div>'

    alias_html = ""
    if aliases:
        alias_html = f"""
          <div class="hover-panel-label">Aliases</div>
          <div class="hover-panel-text">{html.escape(", ".join(aliases))}</div>
"""

    excerpt_block = """
          <div class="hover-panel-label">Excerpts</div>
          <div class="hover-panel-text">(none in current assignment output)</div>
"""
    if excerpts:
        excerpt_block = f"""
          <div class="hover-panel-label">Excerpts</div>
          {excerpts_html}
"""

    return f"""
          <foreignObject class="hover-panel" x="{panel_x}" y="{panel_y}" width="{panel_width}" height="{panel_height}">
            <div xmlns="http://www.w3.org/1999/xhtml" class="hover-panel-box">
              <div class="hover-panel-title">{html.escape(node["name"])}</div>
              <div class="hover-panel-label">Parents</div>
              <div class="hover-panel-text">{html.escape(", ".join(parent_names) if parent_names else "(root topic)")}</div>
              <div class="hover-panel-label">Children</div>
              <div class="hover-panel-text">{html.escape(", ".join(child_names) if child_names else "(none)")}</div>
              {alias_html}
              {excerpt_block}
            </div>
          </foreignObject>"""


def build_node_tooltip(
    node: dict[str, Any],
    parent_ids: set[str],
    child_ids: set[str],
    nodes: dict[str, dict[str, Any]],
    excerpts: list[str],
) -> str:
    parent_names = sorted(nodes[parent_id]["name"] for parent_id in parent_ids if parent_id in nodes)
    child_names = sorted(nodes[child_id]["name"] for child_id in child_ids if child_id in nodes)
    aliases = node.get("aliases") or []
    parts = [
        node["name"],
        f"Parents: {', '.join(parent_names) if parent_names else '(root topic)'}",
        f"Children: {', '.join(child_names) if child_names else '(none)'}",
    ]
    if aliases:
        parts.append(f"Aliases: {', '.join(aliases)}")
    if excerpts:
        parts.append("Excerpts:")
        parts.extend(f"- {excerpt}" for excerpt in excerpts[:5])
        if len(excerpts) > 5:
            parts.append(f"- ... {len(excerpts) - 5} more")
    return "\n".join(parts)


def wrap_label(value: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(value, width=width, break_long_words=False, placeholder="...")
    if not lines:
        return [""]
    if len(lines) <= max_lines:
        return lines
    clipped = lines[:max_lines]
    clipped[-1] = clipped[-1][: max(width - 3, 1)].rstrip() + "..."
    return clipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Render analysis JSON as standalone HTML.")
    parser.add_argument("--input", default="outputs/ontology.json", help="Ontology, demo, or corpus analysis JSON")
    parser.add_argument("--output", default="outputs/ontology.html", help="Output HTML file")
    parser.add_argument("--title", default="Topics Ontology", help="Visualization title")
    parser.add_argument(
        "--view",
        choices=["auto", "ontology", "corpus"],
        default="auto",
        help="Visualization type. Auto detects corpus analysis when trend/competitor keys are present.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.view == "corpus":
        payload = load_corpus_analysis(input_path)
        title = args.title if args.title != "Topics Ontology" else "PSB Corpus Analysis"
        html_output = render_corpus_html(payload, title=title)
        output_kind = "corpus dashboard"
    elif args.view == "auto":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "trend_analysis" in payload and "competitor_analysis" in payload:
            title = args.title if args.title != "Topics Ontology" else "PSB Corpus Analysis"
            html_output = render_corpus_html(payload, title=title)
            output_kind = "corpus dashboard"
        else:
            ontology, excerpts_by_topic_id = load_visualization_data(input_path)
            html_output = render_ontology_html(
                ontology,
                title=args.title,
                excerpts_by_topic_id=excerpts_by_topic_id,
            )
            output_kind = "ontology visualization"
    else:
        ontology, excerpts_by_topic_id = load_visualization_data(input_path)
        html_output = render_ontology_html(
            ontology,
            title=args.title,
            excerpts_by_topic_id=excerpts_by_topic_id,
        )
        output_kind = "ontology visualization"

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")
    print(f"Wrote {output_kind} to {output_path}")


if __name__ == "__main__":
    main()
