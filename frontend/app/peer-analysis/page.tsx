import { AppShell, DataStamp, PageHeader } from "../../components/chrome";
import { PeerAnalysisWorkspace } from "../../components/peer-analysis-workspace";
import { data, getBanks } from "../../lib/dashboard";

export default function PeerAnalysisPage() {
  return (
    <AppShell active="peer-analysis">
      <PageHeader
        eyebrow="Custom Peer Analysis"
        subtitle="Build financial metric graphs and tables by selecting banks, periods, and metrics."
        title="Financial Peer Workspace"
      />

      <PeerAnalysisWorkspace banks={getBanks()} financialAnalysis={data.financial_analysis} />
      <DataStamp />
    </AppShell>
  );
}
