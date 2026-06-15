'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { getCaseSummary, updateCase } from '@/lib/api';

interface Summary {
  case: { id: number; case_number: string; client_id: number; status: string; goal: string; notes: string; assigned_to: string; created_at: string; };
  reports_uploaded: number;
  tradelines_total: number;
  tradelines_derogatory: number;
  findings_total: number;
  findings_high: number;
  dispute_rounds: number;
  outcomes: number;
}

const STATUSES = ['intake', 'active', 'on_hold', 'closed'];

export default function CaseDashboard() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCaseSummary(caseId).then(setData).finally(() => setLoading(false));
  }, [caseId]);

  async function changeStatus(status: string) {
    setSaving(true);
    await updateCase(caseId, { status });
    getCaseSummary(caseId).then(setData).finally(() => setSaving(false));
  }

  if (loading) return <div className="main-layout"><Sidebar /><main className="main-content"><div className="spinner" /></main></div>;
  if (!data) return <div className="main-layout"><Sidebar /><main className="main-content"><p>Case not found.</p></main></div>;

  const c = data.case;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Case <code>{c.case_number}</code></h1>
            <p><Link href={`/clients/${c.client_id}`}>Client #{c.client_id}</Link> · Opened {new Date(c.created_at).toLocaleDateString()}</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select value={c.status} onChange={e => changeStatus(e.target.value)} disabled={saving}
              style={{ padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}>
              {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
          </div>
        </div>

        <CaseNav caseId={caseId} />

        <div className="stat-grid">
          <div className="stat-card"><div className="label">Reports Uploaded</div><div className="value">{data.reports_uploaded}</div></div>
          <div className="stat-card"><div className="label">Total Tradelines</div><div className="value">{data.tradelines_total}</div></div>
          <div className="stat-card"><div className="label">Derogatory Items</div><div className="value" style={{ color: data.tradelines_derogatory > 0 ? 'var(--danger)' : 'inherit' }}>{data.tradelines_derogatory}</div></div>
          <div className="stat-card"><div className="label">Findings</div><div className="value">{data.findings_total}</div></div>
          <div className="stat-card"><div className="label">High Severity</div><div className="value" style={{ color: data.findings_high > 0 ? 'var(--danger)' : 'inherit' }}>{data.findings_high}</div></div>
          <div className="stat-card"><div className="label">Dispute Rounds</div><div className="value">{data.dispute_rounds}</div></div>
          <div className="stat-card"><div className="label">Outcomes Logged</div><div className="value" style={{ color: 'var(--success)' }}>{data.outcomes}</div></div>
        </div>

        {c.goal && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Client Goal</h3>
            <p>{c.goal}</p>
          </div>
        )}

        <div className="card">
          <h3>Quick Actions</h3>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <Link href={`/cases/${caseId}/reports`} className="btn btn-outline">Upload Report</Link>
            <Link href={`/cases/${caseId}/tradelines`} className="btn btn-outline">View Tradelines</Link>
            <Link href={`/cases/${caseId}/comparison`} className="btn btn-outline">Run Comparison</Link>
            <Link href={`/cases/${caseId}/findings`} className="btn btn-outline">Generate Findings</Link>
            <Link href={`/cases/${caseId}/strategy`} className="btn btn-outline">Build Strategy</Link>
            <Link href={`/cases/${caseId}/disputes`} className="btn btn-outline">Manage Disputes</Link>
          </div>
        </div>

        {c.notes && (
          <div className="card">
            <h3>Notes</h3>
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>{c.notes}</p>
          </div>
        )}
      </main>
    </div>
  );
}
