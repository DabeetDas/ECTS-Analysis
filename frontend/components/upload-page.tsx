"use client";

import { useRef, useState } from "react";
import {
    createRun,
    extractFinancials,
    generateInsights,
    retrieveEvidence,
    uploadFiles,
    type ExtractedFinancials,
    type PipelineMetricInsight,
    type PipelineResult,
} from "../lib/pipeline-api";
import { AppShell, DataStamp, PageHeader } from "./chrome";

// ─── Types ────────────────────────────────────────────────────────────────────

type PipelineStep = {
    id: string;
    label: string;
    status: "pending" | "running" | "done" | "error";
};

const INITIAL_STEPS: PipelineStep[] = [
    { id: "create", label: "Create run session", status: "pending" },
    { id: "upload", label: "Upload documents to backend", status: "pending" },
    { id: "extract", label: "Gemini: Extract financials from presentation", status: "pending" },
    { id: "evidence", label: "ReACT: Retrieve transcript evidence", status: "pending" },
    { id: "insights", label: "LLaMA-70B: Synthesize analyst insights", status: "pending" },
    { id: "verify", label: "Verifier: Check for unsupported claims", status: "pending" },
];

// ─── Main Component ────────────────────────────────────────────────────────────

export function UploadPageContent() {
    const [presentation, setPresentation] = useState<File | null>(null);
    const [transcript, setTranscript] = useState<File | null>(null);
    const [steps, setSteps] = useState<PipelineStep[]>(INITIAL_STEPS);
    const [result, setResult] = useState<PipelineResult | null>(null);
    const [activeMetric, setActiveMetric] = useState<string | null>(null);
    const [analystNote, setAnalystNote] = useState("");
    const [running, setRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const resultsRef = useRef<HTMLDivElement>(null);

    function setStep(id: string, status: PipelineStep["status"]) {
        setSteps((prev) =>
            prev.map((step) => (step.id === id ? { ...step, status } : step))
        );
    }

    async function handleRun() {
        if (!presentation && !transcript) {
            setError("Upload at least one file before running.");
            return;
        }
        setError(null);
        setResult(null);
        setActiveMetric(null);
        setRunning(true);
        setSteps(INITIAL_STEPS.map((s) => ({ ...s, status: "pending" })));

        try {
            setStep("create", "running");
            const { run_id } = await createRun();
            setStep("create", "done");

            setStep("upload", "running");
            await uploadFiles(run_id, presentation, transcript, analystNote);
            setStep("upload", "done");

            setStep("extract", "running");
            await extractFinancials(run_id);
            setStep("extract", "done");

            setStep("evidence", "running");
            await retrieveEvidence(run_id);
            setStep("evidence", "done");

            setStep("insights", "running");
            const finalResult = await generateInsights(run_id);
            setStep("insights", "done");

            setStep("verify", "done");
            setResult(finalResult);

            setTimeout(() => {
                resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 200);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            setError(message);
            setSteps((prev) =>
                prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s))
            );
        } finally {
            setRunning(false);
        }
    }

    return (
        <AppShell active="upload">
            <PageHeader
                eyebrow="Agentic Upload Pipeline"
                title="Upload & Analyze"
                subtitle="Upload an investor presentation and earnings call transcript. The pipeline extracts financials via Gemini, links them to transcript evidence, and synthesizes analyst insights via LLaMA-3.3-70B."
            />

            {/* ── Upload zone ─────────────────────────────────────────────────────── */}
            <section className="upload-section">
                <div className="upload-grid">
                    <FileDropZone
                        label="Investor Presentation"
                        accept=".pdf,.pptx"
                        hint="PDF or PPTX"
                        icon="📊"
                        file={presentation}
                        onChange={setPresentation}
                    />
                    <FileDropZone
                        label="Earnings Call Transcript"
                        accept=".txt,.pdf"
                        hint="TXT or PDF"
                        icon="🎙️"
                        file={transcript}
                        onChange={setTranscript}
                    />
                </div>

                <div className="upload-note-panel">
                    <label htmlFor="analyst-note" className="upload-note-label">
                        Analyst note (optional)
                    </label>
                    <textarea
                        id="analyst-note"
                        value={analystNote}
                        onChange={(e) => setAnalystNote(e.target.value)}
                        placeholder="Add a short note for the analyst workflow, context, or special instructions."
                        rows={4}
                        className="upload-note-input"
                        style={{ width: "100%", resize: "vertical", minHeight: "96px", padding: "0.85rem", borderRadius: "0.75rem", border: "1px solid var(--border)" }}
                    />
                </div>

                <div className="upload-actions">
                    <button
                        className="run-button"
                        disabled={running || (!presentation && !transcript)}
                        onClick={handleRun}
                    >
                        {running ? (
                            <>
                                <span className="btn-spinner" />
                                Running Pipeline…
                            </>
                        ) : (
                            <>▶ Run Analysis</>
                        )}
                    </button>
                    {error && <p className="upload-error">⚠ {error}</p>}
                </div>

                {/* ── Pipeline progress ─────────────────────────────────────────────── */}
                {steps.some((s) => s.status !== "pending") && (
                    <div className="pipeline-steps">
                        <p className="eyebrow">Pipeline Progress</p>
                        <ol className="step-list">
                            {steps.map((step) => (
                                <li key={step.id} className={`step-item step-${step.status}`}>
                                    <span className="step-icon">
                                        {step.status === "done" ? "✓" : step.status === "running" ? "…" : step.status === "error" ? "✗" : "○"}
                                    </span>
                                    {step.label}
                                </li>
                            ))}
                        </ol>
                    </div>
                )}
            </section>

            {/* ── Results ─────────────────────────────────────────────────────────── */}
            {result && (
                <div ref={resultsRef}>
                    {result.analyst_note ? (
                        <section className="analysis-note-result" style={{ marginBottom: "1.5rem", padding: "1rem", background: "var(--surface-alt)", borderRadius: "1rem" }}>
                            <p className="eyebrow">Analyst note</p>
                            <p style={{ margin: "0.5rem 0 0", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                                {result.analyst_note}
                            </p>
                        </section>
                    ) : null}
                    <FinancialsSection financials={result.financials} warnings={result.warnings} />
                    {result.insights.length > 0 && (
                        <InsightsSection
                            insights={result.insights}
                            activeMetric={activeMetric}
                            onSelect={setActiveMetric}
                        />
                    )}
                </div>
            )}

            <DataStamp />
        </AppShell>
    );
}

// ─── File Drop Zone ────────────────────────────────────────────────────────────

function FileDropZone({
    label,
    accept,
    hint,
    icon,
    file,
    onChange,
}: {
    label: string;
    accept: string;
    hint: string;
    icon: string;
    file: File | null;
    onChange: (f: File | null) => void;
}) {
    const inputRef = useRef<HTMLInputElement>(null);

    function handleDrop(evt: React.DragEvent) {
        evt.preventDefault();
        const dropped = evt.dataTransfer.files[0];
        if (dropped) onChange(dropped);
    }

    return (
        <div
            className={`drop-zone${file ? " drop-zone--active" : ""}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            aria-label={`Upload ${label}`}
        >
            <input
                type="file"
                accept={accept}
                ref={inputRef}
                style={{ display: "none" }}
                onChange={(e) => onChange(e.target.files?.[0] ?? null)}
            />
            <div className="drop-zone-icon">{icon}</div>
            <p className="drop-zone-label">{label}</p>
            {file ? (
                <p className="drop-zone-file">
                    {file.name} <span>({(file.size / 1024).toFixed(1)} KB)</span>
                </p>
            ) : (
                <p className="drop-zone-hint">Click or drag & drop · {hint}</p>
            )}
        </div>
    );
}

// ─── Financials Section ────────────────────────────────────────────────────────

function FinancialsSection({
    financials,
    warnings,
}: {
    financials: ExtractedFinancials | null;
    warnings: string[];
}) {
    if (!financials) return null;

    const allWarnings = [...(financials.warnings ?? []), ...warnings];
    const groupedByMetric = new Map<string, typeof financials.metrics>();
    for (const metric of financials.metrics) {
        if (!groupedByMetric.has(metric.metric_key)) groupedByMetric.set(metric.metric_key, []);
        groupedByMetric.get(metric.metric_key)!.push(metric);
    }

    return (
        <section style={{ marginBottom: "2rem" }}>
            <div className="section-title" style={{ padding: "0 0 1rem 0" }}>
                <p className="eyebrow">Step 1 Result</p>
                <h3>Extracted Financials{financials.bank_name ? ` — ${financials.bank_name}` : ""}</h3>
            </div>

            {allWarnings.length > 0 && (
                <div className="warning-strip">
                    <strong>Normalization Warnings</strong>
                    <ul>
                        {allWarnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                </div>
            )}

            {financials.periods.length > 0 && (
                <div className="table-wrap compact" style={{ marginBottom: "1.5rem" }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Metric</th>
                                {financials.periods.map((p) => <th key={p}>{p}</th>)}
                                <th>Source</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Array.from(groupedByMetric.entries()).map(([key, values]) => {
                                const byPeriod = new Map(values.map((v) => [v.period, v]));
                                const sample = values[0];
                                return (
                                    <tr key={key}>
                                        <td><strong>{sample.label}</strong></td>
                                        {financials.periods.map((p) => {
                                            const v = byPeriod.get(p);
                                            return (
                                                <td key={p}>
                                                    {v ? formatValue(v.value, v.unit) : <span style={{ opacity: 0.3 }}>—</span>}
                                                </td>
                                            );
                                        })}
                                        <td style={{ fontSize: "11px", opacity: 0.7 }}>
                                            {sample.source?.slide ? `Slide ${sample.source.slide}` : sample.source?.page ? `p.${sample.source.page}` : "—"}
                                        </td>
                                        <td>
                                            <span className={`conf-badge conf-${confidenceLevel(sample.confidence)}`}>
                                                {Math.round(sample.confidence * 100)}%
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {financials.metrics.length === 0 && (
                <p className="empty">No metrics could be extracted from the presentation. Ensure it is a valid investor presentation PDF or PPTX.</p>
            )}
        </section>
    );
}

// ─── Insights Section ──────────────────────────────────────────────────────────

function InsightsSection({
    insights,
    activeMetric,
    onSelect,
}: {
    insights: PipelineMetricInsight[];
    activeMetric: string | null;
    onSelect: (key: string | null) => void;
}) {
    const active = insights.find((i) => i.metric_key === activeMetric) ?? null;

    return (
        <section style={{ marginBottom: "2rem" }}>
            <div className="section-title" style={{ padding: "0 0 1rem 0" }}>
                <p className="eyebrow">Step 2 Result</p>
                <h3>Metric Insights — click a card to expand</h3>
            </div>

            <div className="insight-card-grid">
                {insights.map((insight) => (
                    <InsightCard
                        key={insight.metric_key}
                        insight={insight}
                        active={activeMetric === insight.metric_key}
                        onSelect={() => onSelect(activeMetric === insight.metric_key ? null : insight.metric_key)}
                    />
                ))}
            </div>

            {active && <InsightDrawer insight={active} onClose={() => onSelect(null)} />}
        </section>
    );
}

function InsightCard({
    insight,
    active,
    onSelect,
}: {
    insight: PipelineMetricInsight;
    active: boolean;
    onSelect: () => void;
}) {
    const direction =
        insight.current_value !== null && insight.previous_value !== null
            ? insight.current_value > insight.previous_value
                ? "up"
                : insight.current_value < insight.previous_value
                    ? "down"
                    : "flat"
            : null;

    return (
        <button
            className={`insight-card${active ? " insight-card--active" : ""}`}
            onClick={onSelect}
            aria-pressed={active}
        >
            <div className="insight-card-header">
                <span className="insight-label">{insight.label}</span>
                <span className={`coverage-pill coverage-${insight.coverage}`}>
                    {insight.coverage === "fy25" ? "FY25" : "Multi-Year"}
                </span>
            </div>
            <div className="insight-value">
                {insight.current_value !== null
                    ? `${formatValue(insight.current_value, insight.coverage === "fy25" ? "crore" : "percent")} ${insight.current_period ?? ""}`
                    : "N/A"}
                {direction && (
                    <span className={`direction-arrow direction-${direction}`}>
                        {direction === "up" ? " ↑" : direction === "down" ? " ↓" : " →"}
                    </span>
                )}
            </div>
            <div className="insight-card-footer">
                <span className={`evidence-badge evidence-${insight.evidence_strength}`}>
                    {insight.evidence_strength.toUpperCase()}
                </span>
                <span style={{ fontSize: "11px", opacity: 0.6 }}>
                    {insight.evidence.length} excerpt{insight.evidence.length !== 1 ? "s" : ""}
                </span>
            </div>
        </button>
    );
}

function InsightDrawer({
    insight,
    onClose,
}: {
    insight: PipelineMetricInsight;
    onClose: () => void;
}) {
    return (
        <div className="insight-drawer">
            <div className="insight-drawer-header">
                <div>
                    <span className="eyebrow">Analytical Hub</span>
                    <h3>{insight.label}</h3>
                </div>
                <button className="drawer-close" onClick={onClose} aria-label="Close">✕</button>
            </div>

            <div className="insight-drawer-body">
                {/* Analyst takeaway */}
                <div className="drawer-section">
                    <p className="premium-section-title">Senior Analyst Synthesis</p>
                    <div className="takeaway-card" style={{ background: "var(--pro-accent-soft)", borderLeft: "4px solid var(--pro-accent)" }}>
                        <div className="detailed-analysis-text" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "15px" }}>
                            {insight.analyst_takeaway || "LLaMA synthesis unavailable; showing numeric decomposition below."}
                        </div>
                    </div>
                </div>

                {/* Verifier warnings */}
                {insight.verifier_warnings.length > 0 && (
                    <div className="warning-strip" style={{ margin: "0 0 1rem 0" }}>
                        <strong>Verifier Warnings</strong>
                        <ul>{insight.verifier_warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
                    </div>
                )}

                {/* Numeric notes */}
                {insight.numeric_notes.length > 0 && (
                    <div className="drawer-section">
                        <p className="premium-section-title">Numeric Context</p>
                        <ul className="insight-evidence-list" style={{ listStyle: "none", paddingLeft: 0 }}>
                            {insight.numeric_notes.map((note, i) => (
                                <li key={i} style={{ marginBottom: "6px", fontSize: "13px" }}>{note}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Transcript evidence */}
                {insight.evidence.length > 0 && (
                    <div className="drawer-section">
                        <p className="premium-section-title">
                            Transcript Evidence&nbsp;
                            <span className={`evidence-badge evidence-${insight.evidence_strength}`}>
                                {insight.evidence_strength.toUpperCase()}
                            </span>
                        </p>
                        {insight.evidence.map((item, i) => (
                            <div key={i} className="premium-evidence-item" style={{ marginBottom: "14px", paddingBottom: "10px", borderBottom: i < insight.evidence.length - 1 ? "1px solid var(--line-soft)" : "none" }}>
                                <div style={{ fontSize: "11px", marginBottom: "4px" }}>
                                    <span style={{ fontWeight: 800, color: "var(--pro-accent)" }}>[{i + 1}] {item.topic}</span>
                                    <span style={{ float: "right", opacity: 0.6 }}>{item.source_chunk_id} · score {item.score}</span>
                                </div>
                                <blockquote style={{ margin: 0, fontSize: "12px", color: "var(--muted)", fontStyle: "italic" }}>
                                    {item.excerpt}
                                </blockquote>
                            </div>
                        ))}
                    </div>
                )}

                {insight.needs_analyst_note && (
                    <div className="warning-strip" style={{ marginTop: "1rem" }}>
                        <strong>Analyst Note Needed</strong>
                        <p style={{ margin: 0, fontSize: "13px" }}>
                            No direct transcript evidence found for this metric. Consider adding a manual analyst note.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function formatValue(value: number, unit: string): string {
    if (unit === "crore") {
        if (Math.abs(value) >= 100000) return `${(value / 100000).toFixed(2)} lakh cr`;
        return `${value.toLocaleString("en-IN")} cr`;
    }
    if (unit === "percent") return `${value.toFixed(2)}%`;
    return value.toFixed(2);
}

function confidenceLevel(conf: number): "high" | "medium" | "low" {
    if (conf >= 0.85) return "high";
    if (conf >= 0.65) return "medium";
    return "low";
}
