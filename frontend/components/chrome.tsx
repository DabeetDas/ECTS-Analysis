import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { data, fallbackBrand, getBanks, type Bank } from "../lib/dashboard";

export function AppShell({
  children,
  active,
  bank
}: {
  children: ReactNode;
  active?: "home" | "competitors" | "peer-analysis" | "upload" | string;
  bank?: Bank;
}) {
  const brand = bank?.brand ?? fallbackBrand;
  const banks = getBanks();

  return (
    <main
      className="dashboard"
      style={
        {
          "--bank-primary": brand.primary,
          "--bank-secondary": brand.secondary,
          "--bank-accent": brand.accent
        } as CSSProperties
      }
    >
      <aside className="sidebar" aria-label="Dashboard navigation">
        <div>
          <p className="eyebrow">Earnings Intelligence</p>
          <h1>PSB Bank Lens</h1>
        </div>
        <nav>
          <Link className={active === "home" ? "active" : ""} href="/">
            Overview
          </Link>
          <Link className={active === "competitors" ? "active" : ""} href="/competitors/">
            Competitors
          </Link>
          <Link className={active === "peer-analysis" ? "active" : ""} href="/peer-analysis/">
            Peer Analysis
          </Link>
          <Link className={active === "upload" ? "active" : ""} href="/upload/">
            ⬆ Upload & Analyze
          </Link>
          {banks.map((item) => (
            <Link
              className={active === item.code ? "active" : ""}
              href={`/banks/${item.code}/`}
              key={item.code}
            >
              {item.code} Page
            </Link>
          ))}
        </nav>
      </aside>
      <section className="workspace">{children}</section>
    </main>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {subtitle && <p className="topbar-subtitle">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}

export function BankLinks() {
  return (
    <div className="bank-switcher" aria-label="Bank pages">
      {getBanks().map((bank) => (
        <Link
          href={`/banks/${bank.code}/`}
          key={bank.code}
          style={
            {
              "--chip-color": bank.brand?.primary ?? fallbackBrand.primary
            } as CSSProperties
          }
        >
          {bank.code}
        </Link>
      ))}
    </div>
  );
}

export function Metric({
  label,
  value,
  tone
}: {
  label: string;
  value: number | string;
  tone?: "good" | "watch";
}) {
  return (
    <article className={`metric ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export function DataStamp() {
  return (
    <p className="data-stamp">
      Made with ❤️ for financial analysis
    </p>
  );
}
