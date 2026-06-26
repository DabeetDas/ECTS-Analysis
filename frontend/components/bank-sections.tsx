import { useState, type RefObject } from "react";
import {
  countTopics,
  formatPercent,
  type DocumentRow,
  type FinancialRow,
  type Observation,
  type TopicCount,
  type Trend
} from "../lib/dashboard";
import { Metric } from "./chrome";
import { FinancialInsightsPanel } from "./metric-insight-panel";
import { type MetricInsight } from "../lib/metric-insights";

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

export function FinancialPanel({
  bankCode,
  rows,
  observations,
  onExplain,
  activeMetric
}: {
  bankCode: string;
  rows: FinancialRow[];
  observations: Observation[];
  onExplain?: (metricKey: string) => void;
  activeMetric?: string | null;
}) {
  return (
    <FinancialInsightsPanel
      activeMetric={activeMetric}
      bankCode={bankCode}
      observations={observations}
      onExplain={onExplain}
      rows={rows}
    />
  );
}

export function QualitativePanel({
  documents,
  observations,
  activeInsight,
  llmTakeaway,
  status,
  hubRef,
  onExplain
}: {
  documents: DocumentRow[];
  observations: Observation[];
  activeInsight?: MetricInsight | null;
  llmTakeaway?: string;
  status?: string;
  hubRef?: RefObject<HTMLDivElement>;
  onExplain?: (metricKey: string) => void;
}) {
  const [targetMetric, setTargetMetric] = useState("gnpa_pct");

  const availableMetrics = [
    { key: "gnpa_pct", label: "GNPA %" },
    { key: "nnpa_pct", label: "NNPA %" },
    { key: "roa_pct", label: "ROA %" },
    { key: "nim_pct", label: "NIM %" },
    { key: "efficiency_ratio_pct", label: "Efficiency Ratio" },
    { key: "casa_pct", label: "CASA %" },
    { key: "crar_pct", label: "CRAR %" },
    { key: "lcr_pct", label: "LCR %" },
    { key: "z_score", label: "Bank Z Score" },
    { key: "profit_after_tax_cr", label: "Profit After Tax" },
    { key: "total_expenditure_cr", label: "Total Expenditure" },
    { key: "total_business_cr", label: "Total Business/Income" },
  ];
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
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
            const topTopics = countTopics(callObservations).slice(0, 7);
            const excerpts = callObservations.flatMap((observation) => observation.excerpts ?? []).slice(0, 5);
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
      {/* ANALYTICAL HUB (INLINE EXPLAINER) */}
      <div ref={hubRef} className="premium-insight-modal" style={{
        width: '100%',
        maxWidth: 'none',
        maxHeight: 'none',
        position: 'relative',
        animation: 'none',
        borderRadius: '0',
        border: '1px solid var(--line)',
        background: 'var(--paper)',
        flexDirection: 'column',
        overflow: 'hidden',
        display: status === 'idle' || activeInsight || status === 'loading' ? 'flex' : 'none'
      }}>
        {status === "idle" && !activeInsight && (
          <div style={{ padding: '40px', background: 'var(--pro-accent-soft)', border: '2px dashed var(--pro-accent)', borderRadius: '12px', margin: '20px', textAlign: 'center' }}>
            <h4 style={{ marginBottom: '12px', color: 'var(--pro-accent)', fontSize: '18px' }}>Launch Analytical Synthesis</h4>
            <p style={{ marginBottom: '24px', color: 'var(--muted)', fontSize: '14px' }}>Select a specific financial metric to generate a detailed LLaMA-powered deep dive connecting numbers to transcript evidence.</p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <select
                value={targetMetric}
                onChange={(e) => setTargetMetric(e.target.value)}
                style={{ padding: '10px 16px', borderRadius: '8px', border: '1px solid var(--line)', background: 'white', fontSize: '14px', minWidth: '200px' }}
              >
                {availableMetrics.map(m => (
                  <option key={m.key} value={m.key}>{m.label}</option>
                ))}
              </select>
              <button
                onClick={() => onExplain?.(targetMetric)}
                style={{ padding: '10px 24px', borderRadius: '8px', background: 'var(--pro-accent)', color: 'white', fontWeight: 600, border: 'none', cursor: 'pointer' }}
              >
                Explain Metric
              </button>
            </div>
          </div>
        )}
        {status === "loading" ? (
          <div style={{ padding: '60px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="loading-spinner" />
            <p style={{ marginTop: '16px', fontWeight: 600, color: 'var(--muted)' }}>Synthesizing Detailed LLaMA Insights...</p>
          </div>
        ) : activeInsight && (
          <>
            <div className="premium-insight-header" style={{ borderLeft: '4px solid var(--bank-primary)' }}>
              <div className="premium-insight-hero">
                <span className="pill">{activeInsight.metric.coverage === 'fy25' ? 'FY25 Composition' : 'Multi-Year Trend'}</span>
                <h2>Analytical Hub: {activeInsight.metric.label}</h2>
              </div>
            </div>

            <div className="premium-insight-body" style={{ gridTemplateColumns: '1fr 300px' }}>
              <div className="premium-insight-main" style={{ padding: '24px' }}>
                <section style={{ marginBottom: '32px' }}>
                  <div className="premium-section-title">Senior Analyst Synthesis</div>
                  <div className="takeaway-card" style={{ background: 'var(--pro-accent-soft)', borderLeft: '4px solid var(--pro-accent)' }}>
                    {status === "ask_user" ? (
                      <p><strong>Insufficient management commentary found.</strong><br />Consider adding a manual analyst note.</p>
                    ) : (
                      <div className="detailed-analysis-text" style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', fontSize: '15px' }}>
                        {llmTakeaway || "LLaMA synthesis unavailable; showing raw data decomposition."}
                      </div>
                    )}
                  </div>
                </section>

                <section>
                  <div className="premium-section-title">Numeric Context</div>
                  <ul className="insight-evidence-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
                    {activeInsight.numericNotes.map((note, i) => (
                      <li key={i} style={{ marginBottom: '8px', fontSize: '13px' }}>{note}</li>
                    ))}
                  </ul>
                </section>
              </div>

              <div className="premium-insight-sidebar" style={{ padding: '20px', borderLeft: '1px solid var(--line)' }}>
                <div className="premium-section-title">Evidence Excerpts</div>
                <div className={`evidence-strength ${activeInsight.evidenceStrength}`} style={{ marginBottom: '16px' }}>
                  {activeInsight.evidenceStrength.toUpperCase()} MATCH
                </div>
                {activeInsight.evidence.map((item, i, arr) => (
                  <div key={i} className="premium-evidence-item" style={{ marginBottom: '16px', paddingBottom: '12px', borderBottom: i < arr.length - 1 ? '1px solid var(--line-soft)' : 'none' }}>
                    <div className="premium-evidence-meta" style={{ marginBottom: '4px', fontSize: '11px' }}>
                      <span style={{ fontWeight: 800, color: 'var(--pro-accent)' }}>[{i + 1}] {item.topic}</span>
                      <span style={{ float: 'right', opacity: 0.7 }}>{item.callDate}</span>
                    </div>
                    <blockquote className="premium-evidence-excerpt" style={{ fontSize: '12px', margin: 0, color: 'var(--muted)' }}>
                      {item.excerpt}
                    </blockquote>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div >
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
