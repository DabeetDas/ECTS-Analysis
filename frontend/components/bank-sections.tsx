import {
  countTopics,
  formatCrore,
  formatPercent,
  type DocumentRow,
  type FinancialRow,
  type Observation,
  type TopicCount,
  type Trend
} from "../lib/dashboard";
import { Metric } from "./chrome";

export function BankHero({
  label,
  code,
  documents,
  observations,
  financialRows
}: {
  label: string;
  code: string;
  documents: DocumentRow[];
  observations: Observation[];
  financialRows: FinancialRow[];
}) {
  return (
    <section className="profile-grid">
      <div className="profile-hero">
        <div>
          <p className="eyebrow">Bank Page</p>
          <h2>{label} ({code})</h2>
          <p>Individual quantitative and qualitative insights only. Peer comparison lives on the competitor page.</p>
        </div>
      </div>
      <div className="metric-grid bank-metrics">
        <Metric label="Transcripts" value={documents.length} />
        <Metric label="Observations" value={observations.length} />
        <Metric label="Unique Topics" value={new Set(observations.map((item) => item.topic_name)).size} />
        <Metric label="Financial Years" value={financialRows.length} />
      </div>
    </section>
  );
}

export function FinancialPanel({ rows }: { rows: FinancialRow[] }) {
  const latest = rows[rows.length - 1];

  return (
    <article className="panel financial-panel">
      <div className="section-title">
        <p className="eyebrow">Quantitative</p>
        <h3>3-Year Financial Analysis</h3>
      </div>
      {latest ? (
        <div className="mini-metrics">
          <Metric label="Latest Year" value={latest.fiscal_year} />
          <Metric label="Total Business" value={formatCrore(latest.total_business_cr)} />
          <Metric label="PAT" value={formatCrore(latest.profit_after_tax_cr)} />
          <Metric label="GNPA" value={formatPercent(latest.gnpa_pct)} />
        </div>
      ) : (
        <p className="empty">No financial rows found for this bank.</p>
      )}
      {rows.length > 0 && (
        <div className="table-wrap compact">
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Total Business</th>
                <th>PAT</th>
                <th>ROA</th>
                <th>NIM</th>
                <th>GNPA</th>
                <th>NNPA</th>
                <th>CASA</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.fiscal_year}>
                  <td>{row.fiscal_year}</td>
                  <td>{formatCrore(row.total_business_cr)}</td>
                  <td>{formatCrore(row.profit_after_tax_cr)}</td>
                  <td>{formatPercent(row.roa_pct)}</td>
                  <td>{formatPercent(row.nim_pct)}</td>
                  <td>{formatPercent(row.gnpa_pct)}</td>
                  <td>{formatPercent(row.nnpa_pct)}</td>
                  <td>{formatPercent(row.casa_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

export function QualitativePanel({
  documents,
  observations
}: {
  documents: DocumentRow[];
  observations: Observation[];
}) {
  const dates = Array.from(
    new Set([
      ...documents.map((document) => document.call_date),
      ...observations.map((observation) => observation.call_date)
    ])
  )
    .filter(Boolean)
    .sort()
    .reverse()
    .slice(0, 4);

  const documentsByDate = new Map(documents.map((document) => [document.call_date, document]));

  return (
    <article className="panel qualitative-panel">
      <div className="section-title">
        <p className="eyebrow">Qualitative</p>
        <h3>Latest Transcript Themes</h3>
      </div>
      {dates.length === 0 && <p className="empty">No transcript observations available.</p>}
      <div className="call-stack">
        {dates.map((date) => {
          const document = documentsByDate.get(date);
          const callObservations = observations.filter((observation) => observation.call_date === date);
          const topTopics = countTopics(callObservations).slice(0, 4);
          const excerpts = callObservations.flatMap((observation) => observation.excerpts ?? []).slice(0, 3);
          return (
            <article key={date} className="call-card">
              <div>
                <strong>{document?.quarter ?? "Transcript"}</strong>
                <span>{date}</span>
              </div>
              <p>{topTopics.map(([topic, count]) => `${topic} (${count})`).join(", ") || "No extracted topics"}</p>
              <ul>
                {excerpts.map((excerpt) => (
                  <li key={excerpt}>{excerpt}</li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>
    </article>
  );
}

export function TopicList({
  eyebrow,
  title,
  topics,
  emptyText = "No topics found."
}: {
  eyebrow: string;
  title: string;
  topics: TopicCount[];
  emptyText?: string;
}) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
      </div>
      {topics.length === 0 ? (
        <p className="empty">{emptyText}</p>
      ) : (
        <ol className="ranked-list">
          {topics.slice(0, 12).map((topic) => (
            <li key={topic.topic_name}>
              <span>{topic.topic_name}</span>
              <strong>{topic.mention_count}</strong>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}

export function TrendPanel({ trends }: { trends: Trend[] }) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Movement Across Calls</p>
        <h3>Individual Trend Analysis</h3>
      </div>
      {trends.length === 0 ? (
        <p className="empty">No significant trends at the configured threshold.</p>
      ) : (
        <div className="trend-grid single-bank">
          {trends.map((trend) => (
            <article className="trend-card" key={trend.topic_name}>
              <div className="trend-row">
                <span className={trend.direction}>{trend.direction}</span>
                <strong>{trend.topic_name}</strong>
                <small>tau {trend.kendall_tau} | p {trend.p_value}</small>
              </div>
            </article>
          ))}
        </div>
      )}
    </article>
  );
}

export function ObservationTable({ observations }: { observations: Observation[] }) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Transcript Evidence</p>
        <h3>Bank Observations</h3>
      </div>
      <div className="table-wrap observations">
        <table>
          <thead>
            <tr>
              <th>Quarter</th>
              <th>Date</th>
              <th>Topic</th>
              <th>Mentions</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
            {observations.slice(0, 100).map((observation, index) => (
              <tr key={`${observation.topic_name}-${observation.call_date}-${index}`}>
                <td>{observation.quarter ?? ""}</td>
                <td>{observation.call_date}</td>
                <td>{observation.topic_name}</td>
                <td>{observation.mention_count}</td>
                <td>{(observation.excerpts ?? []).slice(0, 2).join(" | ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
