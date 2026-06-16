'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { runMetro2Analysis, listMetro2Findings } from '@/lib/api';

interface Metro2Finding {
  id: number;
  tradeline_id: number | null;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
  created_at: string;
}

const SEV_COLOR: Record<string, string> = {
  high: 'var(--danger)',
  medium: 'var(--warning)',
  low: 'var(--info)',
  info: 'var(--muted)',
};

const SEV_ORDER = ['high', 'medium', 'low', 'info'];

export default function Metro2Page() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<Metro2Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState('');

  function load() {
    listMetro2Findings(caseId).then(setFindings).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, [caseId]);

  async function runAnalysis() {
    setRunning(true); setError('');
    try {
      const r = await runMetro2Analysis(caseId);
      setSummary(r.severity_summary);
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Analysis failed.');
    } finally { setRunning(false); }
  }

  const grouped: Record<string, Metro2Finding[]> = {};
  findings.forEach(f => {
    const sev = f.severity || 'info';
    if (!grouped[sev]) grouped[sev] = [];
    grouped[sev].push(f);
  });

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Metro 2 Analysis</h1>
            <p>Automated rules engine — DOFD expiry, balance consistency, stale reporting</p>
          </div>
          <button className="btn btn-primary" onClick={runAnalysis} disabled={running}>
            {running ? 'Analyzing…' : '⚡ Run Metro 2 Analysis'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        <div className="disclosure-banner">
          Metro 2 findings are preliminary — they flag potential rule violations for investigator review.
          No finding constitutes a confirmed FCRA violation or guarantee of any outcome.
        </div>

        {error && <div className="alert-error" style={{ marginBottom: 12 }}>{error}</div>}

        {summary && (
          <div className="card" style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
            {SEV_ORDER.map(sev => (
              <div key={sev} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: SEV_COLOR[sev] }}>{summary[sev] ?? 0}</div>
                <div style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--muted)' }}>{sev}</div>
              </div>
            ))}
          </div>
        )}

        {loading ? <div className="spinner" /> : findings.length === 0 ? (
          <div className="card">
            <p className="empty">No Metro 2 findings yet. Click "Run Metro 2 Analysis" to analyze tradelines.</p>
            <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted)', marginTop: 8 }}>
              Metro 2 analysis checks DOFD 7-year reporting windows, balance inconsistencies,
              missing delinquency dates, and stale reporting — no AI API key required.
            </p>
          </div>
        ) : (
          SEV_ORDER.filter(sev => grouped[sev]?.length).map(sev => (
            <div key={sev} style={{ marginBottom: 16 }}>
              <h3 style={{ color: SEV_COLOR[sev], textTransform: 'capitalize', marginBottom: 8 }}>
                {sev} ({grouped[sev].length})
              </h3>
              {grouped[sev].map(f => (
                <div key={f.id} className="card" style={{ marginBottom: 8, borderLeft: `4px solid ${SEV_COLOR[f.severity]}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <strong style={{ color: 'var(--navy)' }}>{f.rule_name}</strong>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {f.fcra_section && <code style={{ fontSize: 11 }}>{f.fcra_section}</code>}
                      <span className={`badge badge-${f.severity === 'high' ? 'high' : f.severity === 'medium' ? 'medium' : 'pending'}`}>
                        {f.rule_code}
                      </span>
                    </div>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>{f.description}</p>
                </div>
              ))}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
