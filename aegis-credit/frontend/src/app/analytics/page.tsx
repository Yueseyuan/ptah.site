'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getAnalyticsSummary, getBureauAccuracy, getDisputeOutcomes, getFindingsTrend } from '@/lib/api';

interface Summary {
  total_cases: number; cases_by_status: Record<string, number>;
  total_clients: number; total_findings: number; findings_by_severity: Record<string, number>;
  findings_reviewed: number; findings_review_rate: number;
  total_tradelines: number; derogatory_tradelines: number; derogatory_rate: number;
  total_outcomes: number; outcomes_by_type: Record<string, number>;
}

interface BureauAccuracy {
  discrepancies_by_type: Record<string, number>; discrepancies_by_severity: Record<string, number>;
  total_discrepancies: number;
}

interface DisputeOutcomes {
  dispute_rounds_by_status: Record<string, number>; outcomes_by_type: Record<string, number>;
  outcomes_by_bureau: Record<string, number>; win_rate: number;
  total_outcomes: number; favorable_outcomes: number;
}

interface FindingsTrend {
  findings_by_type: Record<string, number>; findings_by_status: Record<string, number>;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--accent)' }}>{value}</div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function BreakdownList({ data, title }: { data: Record<string, number>; title: string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  if (!entries.length) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No data</p>;
  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
          <span style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
          <span style={{ fontWeight: 600 }}>{v} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({total ? Math.round(v / total * 100) : 0}%)</span></span>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [bureau, setBureau] = useState<BureauAccuracy | null>(null);
  const [disputes, setDisputes] = useState<DisputeOutcomes | null>(null);
  const [findings, setFindings] = useState<FindingsTrend | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getAnalyticsSummary(),
      getBureauAccuracy(),
      getDisputeOutcomes(),
      getFindingsTrend(),
    ]).then(([s, b, d, f]) => {
      setSummary(s); setBureau(b); setDisputes(d); setFindings(f);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Analytics</h1>
          <p>Platform-wide investigation statistics and dispute performance</p>
        </div>

        {loading ? <div className="spinner" /> : !summary ? <p>Failed to load analytics.</p> : (
          <>
            {/* Overview stat cards */}
            <div className="grid-4" style={{ marginBottom: 24 }}>
              <StatCard label="Total Cases" value={summary.total_cases} />
              <StatCard label="Total Clients" value={summary.total_clients} />
              <StatCard label="Total Findings" value={summary.total_findings} sub={`${summary.findings_review_rate}% reviewed`} />
              <StatCard label="Derogatory Tradelines" value={summary.derogatory_tradelines} sub={`${summary.derogatory_rate}% of all tradelines`} />
            </div>

            {/* Dispute win rate */}
            {disputes && (
              <div className="card" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 32 }}>
                <div style={{ textAlign: 'center', minWidth: 100 }}>
                  <div style={{ fontSize: 48, fontWeight: 800, color: disputes.win_rate >= 50 ? '#16a34a' : '#dc2626' }}>
                    {disputes.win_rate}%
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Dispute Win Rate</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, marginBottom: 4 }}>
                    <strong>{disputes.favorable_outcomes}</strong> favorable outcomes out of <strong>{disputes.total_outcomes}</strong> total
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Deletions, corrections, and updates to reported information
                  </div>
                </div>
              </div>
            )}

            <div className="grid-2" style={{ marginBottom: 24 }}>
              {/* Cases by status */}
              <div className="card">
                <BreakdownList data={summary.cases_by_status} title="Cases by Status" />
              </div>
              {/* Findings by severity */}
              <div className="card">
                <BreakdownList data={summary.findings_by_severity} title="Findings by Severity" />
              </div>
            </div>

            <div className="grid-2" style={{ marginBottom: 24 }}>
              {/* Findings by type */}
              {findings && (
                <div className="card">
                  <BreakdownList data={findings.findings_by_type} title="Findings by Type" />
                </div>
              )}
              {/* Outcomes by type */}
              <div className="card">
                <BreakdownList data={summary.outcomes_by_type} title="Outcomes by Type" />
              </div>
            </div>

            {/* Bureau discrepancies */}
            {bureau && (
              <div className="grid-2">
                <div className="card">
                  <BreakdownList data={bureau.discrepancies_by_type} title="Discrepancy Types" />
                </div>
                <div className="card">
                  <BreakdownList data={bureau.discrepancies_by_severity} title="Discrepancy Severity" />
                </div>
              </div>
            )}

            <div className="card" style={{ marginTop: 24, borderLeft: '3px solid var(--accent)' }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                All statistics are for internal investigation purposes only. Human review required for all findings. This system does not provide legal advice and does not guarantee outcomes.
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
