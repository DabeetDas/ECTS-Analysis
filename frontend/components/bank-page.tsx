import { AppShell, BankLinks, DataStamp, PageHeader } from "./chrome";
import {
  BankHero,
  FinancialPanel,
  ObservationTable,
  QualitativePanel,
  TopicList,
  TrendPanel
} from "./bank-sections";
import {
  getBank,
  getBankDocuments,
  getBankFinancials,
  getBankObservations,
  getBankTopTopics,
  getBankTrends,
  getBankUniqueTopics
} from "../lib/dashboard";

export function BankPageContent({ code }: { code: string }) {
  const bank = getBank(code);
  const documents = getBankDocuments(code);
  const observations = getBankObservations(code);
  const financialRows = getBankFinancials(code);
  const topTopics = getBankTopTopics(code);
  const uniqueTopics = getBankUniqueTopics(code);
  const trends = getBankTrends(code);

  return (
    <AppShell active={code} bank={bank}>
      <PageHeader
        actions={<BankLinks />}
        eyebrow="Individual Bank Insights"
        subtitle="This page excludes peer comparison and focuses only on the selected bank."
        title={`${bank.label} (${bank.code})`}
      />

      <BankHero
        code={bank.code}
        documents={documents}
        financialRows={financialRows}
        label={bank.label}
        observations={observations}
      />

      <section className="two-column individual-grid">
        <FinancialPanel rows={financialRows} />
        <QualitativePanel documents={documents} observations={observations} />
      </section>

      <section className="two-column">
        <TopicList eyebrow="Individual Signals" title="Top Topics" topics={topTopics} />
        <TopicList
          emptyText="No unique topics for this bank in the current run."
          eyebrow="Individual Signals"
          title="Unique Topics"
          topics={uniqueTopics}
        />
      </section>

      <TrendPanel trends={trends} />
      <ObservationTable observations={observations} />
      <DataStamp />
    </AppShell>
  );
}
