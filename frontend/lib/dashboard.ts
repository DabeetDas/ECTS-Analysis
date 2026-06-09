import dashboardData from "../public/data/dashboard-data.json";

export type Brand = {
  primary: string;
  secondary: string;
  accent: string;
};

export type Bank = {
  code: string;
  label: string;
  brand: Brand;
};

export type DocumentRow = {
  company: string;
  call_date: string;
  quarter?: string | null;
  path?: string;
};

export type Observation = {
  company: string;
  call_date: string;
  quarter?: string | null;
  topic_id?: string;
  topic_name: string;
  mention_count: number;
  excerpts?: string[];
};

export type Trend = {
  topic_name: string;
  direction: "up" | "down";
  kendall_tau: number;
  p_value: number;
  sample_excerpts?: string[];
};

export type TopicCount = {
  topic_name: string;
  mention_count: number;
  sample_excerpts?: string[];
};

export type FinancialRow = Record<string, string>;

export type CommonTopic = {
  topic_name: string;
  mention_count?: number;
  companies?: Record<
    string,
    {
      mention_count?: number;
      sample_excerpts?: string[];
    }
  >;
};

export type DashboardPayload = {
  metadata: {
    title: string;
    profile_bank: string;
    generated_from?: string;
  };
  banks: Record<string, Bank>;
  topic_hierarchy: Record<string, string[]>;
  financial_analysis: Record<string, FinancialRow[]>;
  analysis: {
    parameters?: Record<string, unknown>;
    documents?: DocumentRow[];
    observations?: Observation[];
    trend_analysis?: Record<string, Trend[]>;
    competitor_analysis?: {
      jaccard_similarity?: Record<string, Record<string, number>>;
      top_topics_by_company?: Record<string, TopicCount[]>;
      common_topics?: Record<string, CommonTopic[]>;
      unique_topics?: Record<string, TopicCount[]>;
    };
  };
};

export const data = dashboardData as DashboardPayload;

export const fallbackBrand: Brand = {
  primary: "#5C6773",
  secondary: "#0F1E36",
  accent: "#F5F0E6"
};

export function getBanks() {
  return Object.values(data.banks).sort((left, right) => left.label.localeCompare(right.label));
}

export function getBank(code: string) {
  return data.banks[code] ?? {
    code,
    label: code,
    brand: fallbackBrand
  };
}

export function getBankDocuments(code: string) {
  return (data.analysis.documents ?? []).filter((document) => document.company === code);
}

export function getBankObservations(code: string) {
  return (data.analysis.observations ?? []).filter((observation) => observation.company === code);
}

export function getBankFinancials(code: string) {
  return data.financial_analysis[code] ?? [];
}

export function getBankTopTopics(code: string) {
  return data.analysis.competitor_analysis?.top_topics_by_company?.[code] ?? [];
}

export function getBankUniqueTopics(code: string) {
  return data.analysis.competitor_analysis?.unique_topics?.[code] ?? [];
}

export function getBankTrends(code: string) {
  return data.analysis.trend_analysis?.[code] ?? [];
}

export function countTopics(observations: Observation[]) {
  const counts = new Map<string, number>();
  observations.forEach((observation) => {
    counts.set(observation.topic_name, (counts.get(observation.topic_name) ?? 0) + observation.mention_count);
  });
  return Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
}

export function formatCrore(value?: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) {
    return "N/A";
  }
  if (Math.abs(parsed) >= 100000) {
    return `${(parsed / 100000).toFixed(2)} lakh cr`;
  }
  return `${parsed.toLocaleString("en-IN")} cr`;
}

export function formatPercent(value?: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}%` : "N/A";
}

export function heat(value: number) {
  const clamped = Math.max(0, Math.min(1, value));
  const red = Math.round(255 - clamped * 86);
  const green = Math.round(255 - clamped * 44);
  const blue = Math.round(255 - clamped * 92);
  return `rgb(${red}, ${green}, ${blue})`;
}

export function looseMatch(topic: string, subtopic: string) {
  const left = topic.toLowerCase();
  const right = subtopic.toLowerCase();
  return left.includes(right) || right.split(" ").some((part) => part.length > 3 && left.includes(part));
}
