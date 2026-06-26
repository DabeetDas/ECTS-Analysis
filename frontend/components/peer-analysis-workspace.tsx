"use client";

import { useMemo, useState } from "react";
import { formatCrore, formatPercent, type Bank, type FinancialRow } from "../lib/dashboard";

type MetricDefinition = {
  key: string;
  label: string;
  format: "crore" | "percent" | "number";
  description: string;
};

type PeerView = {
  id: number;
  mode: "chart" | "table";
  bankCodes: string[];
  metricKeys: string[];
  years: string[];
};

const metricDefinitions: MetricDefinition[] = [
  { key: "total_income_cr", label: "Total Income", format: "crore", description: "Interest income plus other income, shown in crores." },
  { key: "total_expenditure_cr", label: "Total Expenditure", format: "crore", description: "Interest expended, operating expenses, and provisions, shown in crores." },
  { key: "profit_after_tax_cr", label: "PAT", format: "crore", description: "Profit after tax, shown in crores." },
  { key: "z_score", label: "Bank Z Score", format: "number", description: "Stability indicator using profitability, capital cushion, and earnings volatility." },
  { key: "efficiency_ratio_pct", label: "Efficiency Ratio", format: "percent", description: "Non-interest expense relative to income; lower is generally more efficient." },
  { key: "roa_pct", label: "ROA", format: "percent", description: "Return on assets; profit generated from the bank's asset base." },
  { key: "roe_pct", label: "ROE", format: "percent", description: "Return on equity; profit generated from shareholder equity." },
  { key: "nim_pct", label: "NIM", format: "percent", description: "Net interest margin; lending and investment yield after funding cost." },
  { key: "gnpa_pct", label: "GNPA", format: "percent", description: "Gross non-performing assets as a share of gross advances." },
  { key: "nnpa_pct", label: "NNPA", format: "percent", description: "Net non-performing assets after provisions as a share of net advances." },
  { key: "casa_pct", label: "CASA", format: "percent", description: "Current and savings account deposits as a share of total deposits." },
  { key: "crar_pct", label: "CRAR", format: "percent", description: "Capital to risk-weighted assets ratio; regulatory capital cushion." },
  { key: "lcr_pct", label: "LCR", format: "percent", description: "Liquidity coverage ratio for short-term stressed outflows." },
  { key: "credit_deposit_pct", label: "Credit Deposit", format: "percent", description: "Advances as a share of deposits." },
  { key: "pcr_pct", label: "PCR", format: "percent", description: "Provision coverage ratio for stressed assets." }
];

const fallbackSeriesColors = ["#1E6B7B", "#C27D38", "#6E5974", "#2F5E46", "#8F4F36", "#293241"];

export function PeerAnalysisWorkspace({
  banks,
  financialAnalysis
}: {
  banks: Bank[];
  financialAnalysis: Record<string, FinancialRow[]>;
}) {
  const years = useMemo(() => getYears(financialAnalysis), [financialAnalysis]);
  const availableMetrics = useMemo(
    () => metricDefinitions.filter((metric) => hasMetric(financialAnalysis, metric.key)),
    [financialAnalysis]
  );
  const initialYears = years.slice(-4);
  const initialBanks = banks.map((bank) => bank.code);
  const initialMetrics = availableMetrics
    .filter((metric) => ["z_score", "efficiency_ratio_pct"].includes(metric.key))
    .map((metric) => metric.key);
  const [views, setViews] = useState<PeerView[]>([
    {
      id: 1,
      mode: "chart",
      bankCodes: initialBanks,
      metricKeys: initialMetrics.length ? initialMetrics : availableMetrics.slice(0, 2).map((metric) => metric.key),
      years: initialYears
    }
  ]);

  function addView(mode: PeerView["mode"]) {
    setViews((current) => [
      ...current,
      {
        id: Date.now(),
        mode,
        bankCodes: initialBanks,
        metricKeys: availableMetrics.slice(0, 2).map((metric) => metric.key),
        years: initialYears
      }
    ]);
  }

  function updateView(id: number, updater: (view: PeerView) => PeerView) {
    setViews((current) => current.map((view) => (view.id === id ? updater(view) : view)));
  }

  function removeView(id: number) {
    setViews((current) => current.filter((view) => view.id !== id));
  }

  return (
    <article className="panel peer-builder">
      <div className="section-title peer-builder-title">
        <div>
          <p className="eyebrow">Custom Peer Analysis</p>
          <h3>Financial Metrics Workspace</h3>
        </div>
        <div className="builder-actions">
          <button type="button" onClick={() => addView("chart")}>
            Add Graph
          </button>
          <button type="button" onClick={() => addView("table")}>
            Add Table
          </button>
        </div>
      </div>

      <div className="peer-view-stack">
        {views.map((view, index) => (
          <section className="peer-view" key={view.id}>
            <div className="peer-view-header">
              <h4>{view.mode === "chart" ? "Graph" : "Table"} {index + 1}</h4>
              <div className="view-actions">
                {views.length > 1 && (
                  <button className="remove-view" type="button" onClick={() => removeView(view.id)}>
                    Remove
                  </button>
                )}
              </div>
            </div>

            <div className="peer-controls">
              <SelectorGroup
                label="Banks"
                options={banks.map((bank) => ({ label: bank.code, value: bank.code }))}
                selected={view.bankCodes}
                onChange={(selected) => updateView(view.id, (item) => ({ ...item, bankCodes: selected }))}
              />
              <SelectorGroup
                label="Years"
                options={years.map((year) => ({ label: year, value: year }))}
                selected={view.years}
                onChange={(selected) => updateView(view.id, (item) => ({ ...item, years: selected }))}
              />
              <SelectorGroup
                label="Metrics"
                options={availableMetrics.map((metric) => ({ label: metric.label, value: metric.key }))}
                selected={view.metricKeys}
                onChange={(selected) => updateView(view.id, (item) => ({ ...item, metricKeys: selected }))}
              />
            </div>

            {view.mode === "chart" ? (
              <PeerChart
                banks={banks}
                financialAnalysis={financialAnalysis}
                metrics={availableMetrics}
                view={view}
              />
            ) : (
              <PeerTable
                banks={banks}
                financialAnalysis={financialAnalysis}
                metrics={availableMetrics}
                view={view}
              />
            )}
          </section>
        ))}
      </div>

      <dl className="peer-metric-legend" aria-label="Peer analysis metric meanings">
        {availableMetrics.map((metric) => (
          <div key={metric.key}>
            <dt>{metric.label}</dt>
            <dd>{metric.description}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function SelectorGroup({
  label,
  options,
  selected,
  onChange
}: {
  label: string;
  options: { label: string; value: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
}) {
  return (
    <fieldset className="selector-group">
      <legend>{label}</legend>
      <div>
        {options.map((option) => (
          <label key={option.value}>
            <input
              checked={selected.includes(option.value)}
              type="checkbox"
              onChange={() => onChange(toggleValue(selected, option.value))}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function PeerChart({
  banks,
  financialAnalysis,
  metrics,
  view
}: {
  banks: Bank[];
  financialAnalysis: Record<string, FinancialRow[]>;
  metrics: MetricDefinition[];
  view: PeerView;
}) {
  const series = getSeries({ banks, financialAnalysis, metrics, view });
  const values = series.flatMap((item) => item.points.map((point) => point.value));
  const minValue = Math.min(...values, 0);
  const maxValue = Math.max(...values, 1);
  const range = maxValue - minValue || 1;
  const width = 860;
  const height = 320;
  const padding = { top: 24, right: 24, bottom: 46, left: 64 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  if (!series.length || !view.years.length) {
    return <p className="empty">No plottable values for this selection.</p>;
  }

  const xForYear = (year: string) => {
    const yearIndex = view.years.indexOf(year);
    return padding.left + (view.years.length === 1 ? plotWidth / 2 : (plotWidth * yearIndex) / (view.years.length - 1));
  };
  const yForValue = (value: number) => padding.top + plotHeight - ((value - minValue) / range) * plotHeight;

  return (
    <div className="peer-chart-wrap">
      <svg className="peer-chart" role="img" viewBox={`0 0 ${width} ${height}`} aria-label="Custom peer analysis chart">
        <line x1={padding.left} x2={padding.left} y1={padding.top} y2={padding.top + plotHeight} />
        <line x1={padding.left} x2={padding.left + plotWidth} y1={padding.top + plotHeight} y2={padding.top + plotHeight} />
        {[minValue, minValue + range / 2, maxValue].map((value) => (
          <g key={value}>
            <line
              className="gridline"
              x1={padding.left}
              x2={padding.left + plotWidth}
              y1={yForValue(value)}
              y2={yForValue(value)}
            />
            <text x={padding.left - 10} y={yForValue(value) + 4}>
              {compactNumber(value)}
            </text>
          </g>
        ))}
        {view.years.map((year) => (
          <text key={year} x={xForYear(year)} y={height - 16}>
            {year}
          </text>
        ))}
        {series.map((item, index) => {
          const color = item.color || fallbackSeriesColors[index % fallbackSeriesColors.length];
          const dash = index % 3 === 1 ? "6 5" : index % 3 === 2 ? "2 5" : undefined;
          const path = item.points
            .map((point, pointIndex) => `${pointIndex === 0 ? "M" : "L"} ${xForYear(point.year)} ${yForValue(point.value)}`)
            .join(" ");
          return (
            <g key={item.id}>
              <path d={path} style={{ stroke: color, strokeDasharray: dash }} />
              {item.points.map((point) => (
                <circle cx={xForYear(point.year)} cy={yForValue(point.value)} key={point.year} r="4" style={{ fill: color }} />
              ))}
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        {series.map((item, index) => (
          <span key={item.id}>
            <i style={{ backgroundColor: item.color || fallbackSeriesColors[index % fallbackSeriesColors.length] }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function PeerTable({
  banks,
  financialAnalysis,
  metrics,
  view
}: {
  banks: Bank[];
  financialAnalysis: Record<string, FinancialRow[]>;
  metrics: MetricDefinition[];
  view: PeerView;
}) {
  const selectedMetrics = metrics.filter((metric) => view.metricKeys.includes(metric.key));
  const selectedBanks = banks.filter((bank) => view.bankCodes.includes(bank.code));

  if (!selectedMetrics.length || !selectedBanks.length || !view.years.length) {
    return <p className="empty">No table values for this selection.</p>;
  }

  return (
    <div className="table-wrap peer-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Bank</th>
            <th>Metric</th>
            {view.years.map((year) => (
              <th key={year}>{year}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {selectedBanks.flatMap((bank) =>
            selectedMetrics.map((metric) => (
              <tr key={`${bank.code}-${metric.key}`}>
                <td>{bank.code}</td>
                <td>{metric.label}</td>
                {view.years.map((year) => (
                  <td key={year}>{formatMetricValue(getFinancialValue(financialAnalysis, bank.code, year, metric.key), metric)}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function getSeries({
  banks,
  financialAnalysis,
  metrics,
  view
}: {
  banks: Bank[];
  financialAnalysis: Record<string, FinancialRow[]>;
  metrics: MetricDefinition[];
  view: PeerView;
}) {
  const selectedBanks = banks.filter((bank) => view.bankCodes.includes(bank.code));
  const selectedMetrics = metrics.filter((metric) => view.metricKeys.includes(metric.key));

  return selectedBanks.flatMap((bank) =>
    selectedMetrics.flatMap((metric) => {
      const points = view.years
        .map((year) => ({ year, value: getFinancialValue(financialAnalysis, bank.code, year, metric.key) }))
        .filter((point): point is { year: string; value: number } => Number.isFinite(point.value));
      if (!points.length) {
        return [];
      }
      return [
        {
          id: `${bank.code}-${metric.key}`,
          label: `${bank.code} ${metric.label}`,
          color: bank.brand.primary,
          points
        }
      ];
    })
  );
}

function getFinancialValue(
  financialAnalysis: Record<string, FinancialRow[]>,
  bankCode: string,
  year: string,
  metricKey: string
) {
  const row = financialAnalysis[bankCode]?.find((item) => item.fiscal_year === year);
  const value = Number(row?.[metricKey]);
  return Number.isFinite(value) ? value : NaN;
}

function getYears(financialAnalysis: Record<string, FinancialRow[]>) {
  return Array.from(
    new Set(Object.values(financialAnalysis).flatMap((rows) => rows.map((row) => row.fiscal_year).filter(Boolean)))
  ).sort((left, right) => Number(left.replace(/\D/g, "")) - Number(right.replace(/\D/g, "")));
}

function hasMetric(financialAnalysis: Record<string, FinancialRow[]>, metricKey: string) {
  return Object.values(financialAnalysis).some((rows) => rows.some((row) => row[metricKey]));
}

function toggleValue(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function formatMetricValue(value: number, metric: MetricDefinition) {
  if (!Number.isFinite(value)) {
    return "N/A";
  }
  if (metric.format === "crore") {
    return formatCrore(String(value));
  }
  if (metric.format === "percent") {
    return formatPercent(String(value));
  }
  return value.toFixed(2);
}

function compactNumber(value: number) {
  if (Math.abs(value) >= 100000) {
    return `${(value / 100000).toFixed(1)}L`;
  }
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(value % 1 === 0 ? 0 : 1);
}
