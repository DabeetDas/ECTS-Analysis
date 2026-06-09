import { AppShell, DataStamp, Metric, PageHeader } from "../../components/chrome";
import {
  data,
  getBanks,
  heat,
  looseMatch,
  type Bank,
  type CommonTopic,
  type Observation,
  type TopicCount
} from "../../lib/dashboard";

export default function CompetitorsPage() {
  const banks = getBanks();
  const competitor = data.analysis.competitor_analysis ?? {};
  const matrix = competitor.jaccard_similarity ?? {};
  const commonTopics = competitor.common_topics ?? {};
  const topTopics = competitor.top_topics_by_company ?? {};
  const observations = data.analysis.observations ?? [];
  const pairCount = Object.keys(commonTopics).length;

  return (
    <AppShell active="competitors">
      <PageHeader
        eyebrow="Competitor Analysis"
        subtitle="Comparison-only page for peer overlap, shared themes, and topic concentration by bank."
        title="Public Sector Bank Comparison"
      />

      <section className="metric-grid" aria-label="Comparison parameters">
        <Metric label="Banks Compared" value={banks.length} />
        <Metric label="Comparison Pairs" value={pairCount} />
        <Metric label="Top-N Topics" value={String(data.analysis.parameters?.top_n ?? "N/A")} />
        <Metric label="Alpha" value={String(data.analysis.parameters?.alpha ?? "N/A")} />
      </section>

      <PeerMatrix banks={banks} matrix={matrix} />

      <section className="two-column">
        <TopTopicComparison banks={banks} topTopics={topTopics} />
        <TopicHierarchyComparison observations={observations} />
      </section>

      <CommonTopicPairs commonTopics={commonTopics} />
      <DataStamp />
    </AppShell>
  );
}

function PeerMatrix({
  banks,
  matrix
}: {
  banks: Bank[];
  matrix: Record<string, Record<string, number>>;
}) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Comparison Parameter</p>
        <h3>Topic Overlap Matrix</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Bank</th>
              {banks.map((bank) => (
                <th key={bank.code}>{bank.code}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {banks.map((bank) => (
              <tr key={bank.code}>
                <td>{bank.code}</td>
                {banks.map((peer) => {
                  const value = matrix[bank.code]?.[peer.code] ?? 0;
                  return (
                    <td key={peer.code} style={{ backgroundColor: heat(value) }}>
                      {value.toFixed(4)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function TopTopicComparison({
  banks,
  topTopics
}: {
  banks: Bank[];
  topTopics: Record<string, TopicCount[]>;
}) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Comparison Parameter</p>
        <h3>Top Topics By Bank</h3>
      </div>
      <div className="comparison-stack">
        {banks.map((bank) => (
          <article className="comparison-row" key={bank.code}>
            <span style={{ backgroundColor: bank.brand.primary }} />
            <div>
              <strong>{bank.label}</strong>
              <ol>
                {(topTopics[bank.code] ?? []).slice(0, 5).map((topic) => (
                  <li key={topic.topic_name}>
                    {topic.topic_name} <b>{topic.mention_count}</b>
                  </li>
                ))}
              </ol>
            </div>
          </article>
        ))}
      </div>
    </article>
  );
}

function TopicHierarchyComparison({ observations }: { observations: Observation[] }) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Comparison Parameter</p>
        <h3>Broad Topic Coverage</h3>
      </div>
      <div className="topic-grid compact-topics">
        {Object.entries(data.topic_hierarchy).map(([topic, subtopics]) => {
          const matched = observations.filter((observation) =>
            subtopics.some((subtopic) => looseMatch(observation.topic_name, subtopic))
          );
          const bankCount = new Set(matched.map((observation) => observation.company)).size;
          return (
            <article className="topic-card" key={topic}>
              <div>
                <h4>{topic}</h4>
                <span>{bankCount} banks | {matched.length} signals</span>
              </div>
            </article>
          );
        })}
      </div>
    </article>
  );
}

function CommonTopicPairs({ commonTopics }: { commonTopics: Record<string, CommonTopic[]> }) {
  return (
    <article className="panel">
      <div className="section-title">
        <p className="eyebrow">Comparison Parameter</p>
        <h3>Common Topics Between Banks</h3>
      </div>
      <div className="pair-grid">
        {Object.entries(commonTopics).map(([pair, topics]) => (
          <article className="pair-card" key={pair}>
            <h4>{pair.replace("__", " vs ")}</h4>
            <ol>
              {topics.slice(0, 8).map((topic) => (
                <li key={topic.topic_name}>
                  <strong>{topic.topic_name}</strong>
                  {topic.companies && (
                    <span>
                      {Object.entries(topic.companies)
                        .map(([bank, details]) => `${bank}: ${details.mention_count ?? 0}`)
                        .join(" | ")}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </article>
  );
}
