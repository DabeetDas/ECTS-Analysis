"use client";

import { data, formatCrore, formatPercent, type FinancialRow, type Observation } from "../lib/dashboard";
import {
  getMetricDefinition,
} from "../lib/metric-insights";
import { Metric } from "./chrome";

const financialRatioLegend = [
  ["Bank Z Score", "Stability indicator based on profitability, capital cushion, and earnings volatility."],
  ["Efficiency Ratio", "Non-interest expense relative to income; lower generally signals better operating efficiency."],
  ["ROA", "Return on assets; profit generated for each unit of assets."],
  ["NIM", "Net interest margin; spread earned on interest-bearing assets after funding cost."],
  ["GNPA", "Gross non-performing assets as a share of gross advances."],
  ["NNPA", "Net non-performing assets after provisions as a share of net advances."],
  ["CASA", "Current and savings account deposits as a share of total deposits."],
  ["CRAR", "Capital to risk-weighted assets ratio; overall regulatory capital cushion."],
  ["LCR", "Liquidity coverage ratio; high-quality liquid assets against short-term net cash outflows."]
];

export function FinancialInsightsPanel({
  rows,
}: {
  bankCode: string;
  rows: FinancialRow[];
  observations: Observation[];
  onExplain?: (metricKey: string) => void;
  activeMetric?: string | null;
}) {
  const latest = rows[rows.length - 1];
  const latestBusinessOrIncome = latest?.total_business_cr || latest?.total_income_cr;
  const latestBusinessOrIncomeLabel = latest?.total_business_cr ? "Total Business" : "Total Income";

  if (!latest) {
    return (
      <article className="panel financial-panel">
        <div className="section-title">
          <p className="eyebrow">Quantitative</p>
          <h3>4-Year Financial Analysis</h3>
        </div>
        <p className="empty">No financial rows found for this bank.</p>
      </article>
    );
  }

  return (
    <article className="panel financial-panel">
      <div className="section-title">
        <p className="eyebrow">Quantitative</p>
        <h3>4-Year Financial Analysis</h3>
      </div>
      <div className="mini-metrics">
        <Metric label="Latest Year" value={latest.fiscal_year} />
        <Metric label={latestBusinessOrIncomeLabel} value={formatCrore(latestBusinessOrIncome)} />
        <Metric label="PAT" value={formatCrore(latest.profit_after_tax_cr)} />
        <Metric label="Total Expenditure" value={formatCrore(latest.total_expenditure_cr)} />
      </div>

      <div className="table-wrap compact">
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Bank Z Score</th>
              <th>Efficiency Ratio</th>
              <th>ROA</th>
              <th>NIM</th>
              <th>GNPA</th>
              <th>NNPA</th>
              <th>CASA</th>
              <th>CRAR</th>
              <th>LCR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.fiscal_year}>
                <td>{row.fiscal_year}</td>
                <td>{row.z_score || "N/A"}</td>
                <td>{formatPercent(row.efficiency_ratio_pct)}</td>
                <td>{formatPercent(row.roa_pct)}</td>
                <td>{formatPercent(row.nim_pct)}</td>
                <td>{formatPercent(row.gnpa_pct)}</td>
                <td>{formatPercent(row.nnpa_pct)}</td>
                <td>{formatPercent(row.casa_pct)}</td>
                <td>{formatPercent(row.crar_pct)}</td>
                <td>{formatPercent(row.lcr_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <dl className="ratio-legend" aria-label="Financial ratio meanings">
        {financialRatioLegend.map(([label, meaning]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{meaning}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
