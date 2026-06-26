"use client";

import { useRef, useState } from "react";
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
import { buildMetricInsight, type MetricInsight } from "../lib/metric-insights";

type InsightStatus = "idle" | "loading" | "ready" | "local" | "error" | "ask_user";

export function BankPageContent({ code }: { code: string }) {
  const bank = getBank(code);
  const documents = getBankDocuments(code);
  const observations = getBankObservations(code);
  const financialRows = getBankFinancials(code);
  const topTopics = getBankTopTopics(code);
  const uniqueTopics = getBankUniqueTopics(code);
  const trends = getBankTrends(code);

  const [activeMetric, setActiveMetric] = useState<string | null>(null);
  const [activeInsight, setActiveInsight] = useState<MetricInsight | null>(null);
  const [llmTakeaway, setLlmTakeaway] = useState("");
  const [status, setStatus] = useState<InsightStatus>("idle");
  const hubRef = useRef<HTMLDivElement>(null);

  const handleExplain = async (metricKey: string) => {
    setActiveMetric(metricKey);
    setStatus("loading");
    setLlmTakeaway("");

    // Scroll to hub immediately to show loading state
    hubRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const localInsight = buildMetricInsight({
      metricKey,
      financialRows,
      observations,
      topicHierarchy: { topics: [] } // Mocked or simplified for now, as it's not strictly needed for the fetch
    });

    if (!localInsight) {
      setStatus("error");
      return;
    }

    setActiveInsight(localInsight);

    try {
      const response = await fetch("http://localhost:8000/api/metric-insight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bankCode: code, insight: localInsight })
      });
      if (!response.ok) throw new Error("Backend error");

      const payload = await response.json();
      if (payload.askUser) {
        setStatus("ask_user");
      } else {
        setLlmTakeaway(payload.takeaway || "");
        setStatus(payload.takeaway ? "ready" : "local");
      }
    } catch (err) {
      setStatus("local");
    }
  };

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
        <FinancialPanel
          bankCode={bank.code}
          observations={observations}
          rows={financialRows}
          onExplain={handleExplain}
          activeMetric={activeMetric}
        />
        <QualitativePanel
          documents={documents}
          observations={observations}
          activeInsight={activeInsight}
          llmTakeaway={llmTakeaway}
          status={status}
          hubRef={hubRef}
          onExplain={handleExplain}
        />
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
