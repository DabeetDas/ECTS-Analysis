import { formatCrore, formatPercent, looseMatch, type FinancialRow, type Observation } from "./dashboard";

export type MetricInsightDefinition = {
  key: string;
  label: string;
  format: "crore" | "percent" | "number";
  coverage: "fy25" | "multi-year";
  better: "higher" | "lower" | "contextual";
  topics: string[];
  keywords: string[];
  adjacentMetrics: string[];
};

export type EvidenceItem = {
  topic: string;
  excerpt: string;
  callDate: string;
  quarter?: string | null;
  score: number;
  matchType: "direct" | "expanded" | "keyword";
};

export type MetricInsight = {
  metric: MetricInsightDefinition;
  currentYear: string;
  currentValue: string;
  previousYear?: string;
  previousValue?: string;
  absoluteChange?: string;
  percentChange?: string;
  direction?: "up" | "down" | "flat";
  evidence: EvidenceItem[];
  evidenceStrength: "direct" | "expanded" | "weak";
  localTakeaway: string;
  numericNotes: string[];
};

export const metricInsightDefinitions: MetricInsightDefinition[] = [
  {
    key: "total_income_cr",
    label: "Total Income",
    format: "crore",
    coverage: "fy25",
    better: "higher",
    topics: ["Interest Income", "Non Interest Income", "Fee Income", "Treasury Income", "Loan Growth", "Deposit Pricing"],
    keywords: ["income", "interest income", "fee", "treasury", "loan growth", "business growth"],
    adjacentMetrics: ["nim_pct", "credit_deposit_pct", "casa_pct"]
  },
  {
    key: "profit_after_tax_cr",
    label: "PAT",
    format: "crore",
    coverage: "fy25",
    better: "higher",
    topics: ["Profit Growth", "Operating Profit", "Net Interest Income", "Provisions", "Treasury Gains", "Asset Quality"],
    keywords: ["profit", "pat", "nii", "provision", "recovery", "treasury", "operating profit"],
    adjacentMetrics: ["total_income_cr", "total_expenditure_cr", "nim_pct", "gnpa_pct"]
  },
  {
    key: "total_expenditure_cr",
    label: "Total Expenditure",
    format: "crore",
    coverage: "fy25",
    better: "lower",
    topics: ["Operating Expenses", "Employee Expenses", "Provisions", "Funding Cost", "Technology Spend"],
    keywords: ["expense", "expenditure", "cost", "employee", "provision", "technology", "funding cost"],
    adjacentMetrics: ["efficiency_ratio_pct", "nim_pct", "gnpa_pct"]
  },
  {
    key: "z_score",
    label: "Bank Z Score",
    format: "number",
    coverage: "multi-year",
    better: "higher",
    topics: ["Profitability", "Capital Adequacy", "Asset Quality", "Volatility", "Risk Management"],
    keywords: ["capital", "asset quality", "risk", "profitability", "stability", "volatility"],
    adjacentMetrics: ["roa_pct", "crar_pct", "gnpa_pct"]
  },
  {
    key: "efficiency_ratio_pct",
    label: "Efficiency Ratio",
    format: "percent",
    coverage: "multi-year",
    better: "lower",
    topics: ["Operating Expenses", "Operational Efficiency", "Employee Cost", "Branch Network", "Technology Transformation"],
    keywords: ["efficiency", "operating expense", "employee", "branch", "technology", "cost"],
    adjacentMetrics: ["total_expenditure_cr", "roa_pct"]
  },
  {
    key: "roa_pct",
    label: "ROA",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Return on Assets", "Profitability", "Profit Growth", "Asset Quality"],
    keywords: ["roa", "return on assets", "profitability", "profit", "assets"],
    adjacentMetrics: ["profit_after_tax_cr", "z_score"]
  },
  {
    key: "roe_pct",
    label: "ROE",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Return on Equity", "Profitability", "Shareholder Returns", "Capital Adequacy"],
    keywords: ["roe", "return on equity", "shareholder", "profitability", "capital"],
    adjacentMetrics: ["profit_after_tax_cr", "crar_pct"]
  },
  {
    key: "nim_pct",
    label: "NIM",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Net Interest Margin", "Loan Yields", "Deposit Cost", "Funding Cost", "Interest Rate Repricing"],
    keywords: ["nim", "margin", "yield", "deposit cost", "funding cost", "repricing", "interest rate"],
    adjacentMetrics: ["total_income_cr", "casa_pct", "credit_deposit_pct"]
  },
  {
    key: "gnpa_pct",
    label: "GNPA",
    format: "percent",
    coverage: "multi-year",
    better: "lower",
    topics: ["Gross NPA", "Asset Quality", "Slippages", "Recoveries", "Provisioning"],
    keywords: ["gnpa", "npa", "asset quality", "slippage", "recovery", "provision"],
    adjacentMetrics: ["nnpa_pct", "pcr_pct", "profit_after_tax_cr"]
  },
  {
    key: "nnpa_pct",
    label: "NNPA",
    format: "percent",
    coverage: "multi-year",
    better: "lower",
    topics: ["Net NPA", "Provision Coverage", "Recoveries", "Write-Offs", "Asset Quality"],
    keywords: ["nnpa", "net npa", "provision", "recovery", "write off", "asset quality"],
    adjacentMetrics: ["gnpa_pct", "pcr_pct"]
  },
  {
    key: "casa_pct",
    label: "CASA",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["CASA", "Deposit Growth", "Liability Franchise", "Deposit Pricing", "Funding Cost"],
    keywords: ["casa", "deposit", "savings", "current account", "liability", "funding cost"],
    adjacentMetrics: ["nim_pct", "lcr_pct"]
  },
  {
    key: "crar_pct",
    label: "CRAR",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Capital Adequacy", "Risk Weighted Assets", "Capital Raising", "CET1 Ratio", "Loan Growth Capacity"],
    keywords: ["crar", "capital", "risk weighted", "cet1", "capital adequacy", "rwa"],
    adjacentMetrics: ["z_score", "cet1_pct"]
  },
  {
    key: "lcr_pct",
    label: "LCR",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Liquidity Coverage Ratio", "Liquidity Management", "Deposit Growth", "CASA", "ALM Management"],
    keywords: ["lcr", "liquidity", "alm", "deposit", "hqlA", "cash outflow"],
    adjacentMetrics: ["casa_pct", "credit_deposit_pct"]
  },
  {
    key: "credit_deposit_pct",
    label: "Credit Deposit",
    format: "percent",
    coverage: "multi-year",
    better: "contextual",
    topics: ["Credit Deposit Ratio", "Advances Growth", "Deposit Growth", "Loan Growth", "Liquidity Management"],
    keywords: ["credit deposit", "advances", "deposit growth", "loan growth", "cd ratio"],
    adjacentMetrics: ["lcr_pct", "casa_pct"]
  },
  {
    key: "pcr_pct",
    label: "PCR",
    format: "percent",
    coverage: "multi-year",
    better: "higher",
    topics: ["Provision Coverage Ratio", "Provisioning", "Asset Quality", "Recoveries", "Write-Offs"],
    keywords: ["pcr", "provision coverage", "provision", "npa", "recovery"],
    adjacentMetrics: ["gnpa_pct", "nnpa_pct"]
  }
];

export function getMetricDefinition(metricKey: string) {
  return metricInsightDefinitions.find((metric) => metric.key === metricKey);
}

export function buildMetricInsight({
  metricKey,
  financialRows,
  observations,
  topicHierarchy
}: {
  metricKey: string;
  financialRows: FinancialRow[];
  observations: Observation[];
  topicHierarchy: Record<string, string[]>;
}): MetricInsight | null {
  const metric = getMetricDefinition(metricKey);
  if (!metric) {
    return null;
  }

  const rowsWithMetric = financialRows.filter((row) => isFiniteNumber(row[metric.key]));
  const current = rowsWithMetric[rowsWithMetric.length - 1];
  const previous = metric.coverage === "multi-year" ? rowsWithMetric[rowsWithMetric.length - 2] : undefined;
  if (!current) {
    return null;
  }

  const currentValue = Number(current[metric.key]);
  const previousValue = previous ? Number(previous[metric.key]) : undefined;
  const evidence = retrieveEvidence({ metric, observations, topicHierarchy });
  const evidenceStrength = evidence.some((item) => item.matchType === "direct")
    ? "direct"
    : evidence.length > 0
      ? "expanded"
      : "weak";
  const movement = previousValue === undefined ? undefined : currentValue - previousValue;
  const direction = movement === undefined ? undefined : movement > 0 ? "up" : movement < 0 ? "down" : "flat";
  const percentChange =
    movement === undefined || previousValue === undefined || previousValue === 0 ? undefined : `${((movement / Math.abs(previousValue)) * 100).toFixed(2)}%`;

  const numericNotes = buildNumericNotes({
    metric,
    financialRows,
    current,
    previous,
    currentValue,
    previousValue
  });

  return {
    metric,
    currentYear: current.fiscal_year,
    currentValue: formatMetricValue(currentValue, metric),
    previousYear: previous?.fiscal_year,
    previousValue: previousValue === undefined ? undefined : formatMetricValue(previousValue, metric),
    absoluteChange: movement === undefined ? undefined : formatMetricValue(movement, metric),
    percentChange,
    direction,
    evidence,
    evidenceStrength,
    localTakeaway: buildLocalTakeaway(metric, current, currentValue, previous, previousValue, evidenceStrength),
    numericNotes
  };
}

function retrieveEvidence({
  metric,
  observations,
  topicHierarchy
}: {
  metric: MetricInsightDefinition;
  observations: Observation[];
  topicHierarchy: Record<string, string[]>;
}) {
  const directTopics = new Set(metric.topics.map(normalize));
  const expandedTopics = new Set([
    ...metric.topics.flatMap((topic) => topicHierarchy[topic] ?? []),
    ...metric.adjacentMetrics.flatMap((metricKey) => getMetricDefinition(metricKey)?.topics ?? [])
  ].map(normalize));
  const keywords = metric.keywords.map(normalize);

  return observations
    .flatMap((observation) => {
      const topic = normalize(observation.topic_name);
      const text = normalize(`${observation.topic_name} ${(observation.excerpts ?? []).join(" ")}`);
      const keywordMatches = keywords.filter((keyword) => text.includes(keyword)).length;
      const directMatch = [...directTopics].some((mappedTopic) => looseMatch(topic, mappedTopic) || looseMatch(mappedTopic, topic));
      const expandedMatch = [...expandedTopics].some((mappedTopic) => looseMatch(topic, mappedTopic) || looseMatch(mappedTopic, topic));
      if (!directMatch && !expandedMatch && keywordMatches === 0) {
        return [];
      }
      const matchType = directMatch ? "direct" : expandedMatch ? "expanded" : "keyword";
      const score =
        (directMatch ? 8 : 0) +
        (expandedMatch ? 4 : 0) +
        keywordMatches * 2 +
        Math.min(observation.mention_count, 8);
      // recencyScore(observation.call_date);

      return (observation.excerpts ?? [""]).slice(0, 3).map((excerpt) => ({
        topic: observation.topic_name,
        excerpt,
        callDate: observation.call_date,
        quarter: observation.quarter,
        score,
        matchType: matchType as "direct" | "expanded" | "keyword"
      }));
    })
    .filter((item) => item.excerpt.trim())
    .sort((left, right) => right.score - left.score)
    .slice(0, 8);
}

function buildNumericNotes({
  metric,
  financialRows,
  current,
  previous,
  currentValue,
  previousValue
}: {
  metric: MetricInsightDefinition;
  financialRows: FinancialRow[];
  current: FinancialRow;
  previous?: FinancialRow;
  currentValue: number;
  previousValue?: number;
}) {
  if (metric.coverage === "fy25") {
    const notes = [`${metric.label} is available only for ${current.fiscal_year} in the uploaded workbook.`];
    if (metric.key === "profit_after_tax_cr") {
      notes.push(componentNote(current, "total_income_cr", "Total Income"));
      notes.push(componentNote(current, "total_expenditure_cr", "Total Expenditure"));
    }
    if (metric.key === "total_expenditure_cr") {
      notes.push(componentNote(current, "interest_expended_cr", "Interest Expended"));
      notes.push(componentNote(current, "operating_expenses_cr", "Operating Expenses"));
      notes.push(componentNote(current, "provisions_contingencies_cr", "Provisions and Contingencies"));
    }
    return notes.filter(Boolean);
  }

  if (!previous || previousValue === undefined) {
    return [`${metric.label} has no prior-year value available for comparison.`];
  }

  const direction = currentValue > previousValue ? "increased" : currentValue < previousValue ? "declined" : "was flat";

  const historyString = financialRows
    .filter((row) => isFiniteNumber(row[metric.key]))
    .map((row) => `${row.fiscal_year}: ${formatMetricValue(Number(row[metric.key]), metric)}`)
    .join(", ");

  return [
    `${metric.label} ${direction} from ${formatMetricValue(previousValue, metric)} in ${previous.fiscal_year} to ${formatMetricValue(currentValue, metric)} in ${current.fiscal_year}.`,
    `Historical timeline: ${historyString}`
  ];
}

function buildLocalTakeaway(
  metric: MetricInsightDefinition,
  current: FinancialRow,
  currentValue: number,
  previous: FinancialRow | undefined,
  previousValue: number | undefined,
  evidenceStrength: MetricInsight["evidenceStrength"]
) {
  const evidencePhrase =
    evidenceStrength === "direct"
      ? "Direct transcript evidence was found for this metric."
      : evidenceStrength === "expanded"
        ? "Direct transcript evidence was limited, so adjacent topics were used."
        : "No direct transcript evidence was found; use the numeric decomposition as the primary explanation.";

  if (metric.coverage === "fy25" || !previous || previousValue === undefined) {
    return `${metric.label} is ${formatMetricValue(currentValue, metric)} in ${current.fiscal_year}. YoY movement is not available from the uploaded workbook. ${evidencePhrase}`;
  }

  const direction = currentValue > previousValue ? "up" : currentValue < previousValue ? "down" : "flat";
  return `${metric.label} moved ${direction} from ${previous.fiscal_year} to ${current.fiscal_year}. ${evidencePhrase}`;
}

function componentNote(row: FinancialRow, key: string, label: string) {
  return isFiniteNumber(row[key]) ? `${label}: ${formatCrore(row[key])}.` : "";
}

function formatMetricValue(value: number, metric: MetricInsightDefinition) {
  if (metric.format === "crore") {
    return formatCrore(String(value));
  }
  if (metric.format === "percent") {
    return formatPercent(String(value));
  }
  return value.toFixed(2);
}

function normalize(value: string) {
  return value.toLowerCase();
}

function isFiniteNumber(value?: string) {
  return Number.isFinite(Number(value));
}

function recencyScore(callDate: string) {
  const year = Number(String(callDate).slice(0, 4));
  return Number.isFinite(year) ? Math.max(0, year - 2020) : 0;
}
