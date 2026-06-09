import Link from "next/link";
import { AppShell, BankLinks, DataStamp, Metric, PageHeader } from "../components/chrome";
import { data, getBanks } from "../lib/dashboard";

export default function HomePage() {
  const banks = getBanks();
  const documents = data.analysis.documents ?? [];
  const observations = data.analysis.observations ?? [];
  const uniqueTopics = new Set(observations.map((observation) => observation.topic_name)).size;

  return (
    <AppShell active="home">
      <PageHeader
        actions={<BankLinks />}
        eyebrow="Dashboard Index"
        subtitle="Choose a bank page for individual insights, or open the competitor page for comparison-only analysis."
        title={data.metadata.title}
      />

      <section className="metric-grid" aria-label="Summary metrics">
        <Metric label="Banks" value={banks.length} />
        <Metric label="Documents" value={documents.length} />
        <Metric label="Observations" value={observations.length} />
        <Metric label="Unique Topics" value={uniqueTopics} />
      </section>

      <section className="index-grid">
        <Link className="index-card competitor-card" href="/competitors/">
          <p className="eyebrow">Comparison Page</p>
          <h2>Competitor Analysis</h2>
          <p>Peer overlap matrix, comparison parameters, common topics, and bank-vs-bank topic signals.</p>
        </Link>

        {banks.map((bank) => (
          <Link
            className="index-card"
            href={`/banks/${bank.code}/`}
            key={bank.code}
            style={{ borderLeftColor: bank.brand.primary }}
          >
            <p className="eyebrow">{bank.code} Bank Page</p>
            <h2>{bank.label}</h2>
            <p>Individual financials, qualitative transcript themes, trends, top topics, and observations.</p>
          </Link>
        ))}
      </section>

      <DataStamp />
    </AppShell>
  );
}
