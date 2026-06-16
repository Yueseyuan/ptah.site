'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { runMetro2Analysis, listMetro2Findings } from '@/lib/api';

interface Metro2Finding {
  id: number;
  case_id: number;
  tradeline_id: number | null;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
  created_at: string;
}

const SEVERITY_ORDER = ['high', 'medium', 'low', 'info'];
const SEVERITY_BADGE: Record<string, string> = {
  high: 'badge-high',
  medium: 'badge-medium',
  low: 'badge-low',
  info: 'badge-pending',
};

export default function Metro2Page() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<Metro2Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<{ tradelines_analyzed: number; findings_generated: number; severity_summary: Record<string, number> } | null>(null);
  const [error, setError] = useState('');

  function load() {
    listMetro2Findings(caseId)
      .then(setFindings)
      .catch(() => setFindings([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [caseId]);

  async function runAnalysis() {
    setRunning(true); setError('');
    try {
      const result = await runMetro2Analysis(caseId);
      setSummary({
        tradelines_analyzed: result.tradelines_analyzed,
        findings_generated: result.findings_generated,
        severity_summary: result.severity_summary,
      });
      setFindings(result.items || []);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e?.message || 'Analysis failed.');
    } finally { setRunning(false); }
  }

  const grouped: Record<string, Metro2Finding[]> = {};
  for (const sev of SEVERITY_ORDER) grouped[sev] = [];
  for (const f of findings) {
    const key = SEVERITY_ORDER.includes(f.severity) ? f.severity : 'info';
    grouped[key].push(f);
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Metro 2 Analysis</h1>
            <p>Automated rules engine checking Metro 2 spec compliance and FCRA reporting windows</p>
          </div>
          <button className="btn btn-primary" onClick={runAnalysis} disabled={running}>
            {running ? 'Analyzing…' : 'Run Metro 2 Analysis'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        {summary && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Analysis Summary</h3>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginTop: 8 }}>
              <div><strong>{summary.tradelines_analyzed}</strong> tradelines analyzed</div>
              <div><strong>{summary.findings_generated}</strong> findings generated</div>
              {Object.entries(summary.severity_summary).map(([sev, count]) => (
                count > 0 ? (
                  <div key={sev}>
                    <span className={`badge ${SEVERITY_BADGE[sev] || 'badge-pending'}`}>{sev}</span> {count}
                  </div>
                ) : null
              ))}
            </div>
          </div>
        )}

        {loading ? <div className="spinner" /> : findings.length === 0 ? (
          <div className="card">
            <p className="empty">No Metro 2 findings yet. Click &ldquo;Run Metro 2 Analysis&rdquo; to check your tradelines.</p>
          </div>
        ) : (
          SEVERITY_ORDER.map(sev => {
            const items = grouped[sev];
            if (!items.length) return null;
            return (
              <div key={sev} style={{ marginBottom: 20 }}>
                <h3 style={{ textTransform: 'capitalize', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className={`badge ${SEVERITY_BADGE[sev] || 'badge-pending'}`}>{sev}</span>
                  {items.length} finding{items.length !== 1 ? 's' : ''}
                </h3>
                {items.map(f => (
                  <div key={f.id} className="card" style={{ marginBottom: 10, borderLeft: `4px solid ${sev === 'high' ? 'var(--danger)' : sev === 'medium' ? 'var(--warning)' : 'var(--muted)'}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                      <strong>{f.rule_name}</strong>
                      <div style={{ display: 'flex', gap: 8, flexShrink: 0, marginLeft: 12 }}>
                        <span className={`badge ${SEVERITY_BADGE[f.severity] || 'badge-pending'}`}>{f.severity}</span>
                        {f.fcra_section && <span style={{ fontSize: 11, color: 'var(--muted)' }}>{f.fcra_section}</span>}
                      </div>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>{f.description}</p>
                    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--muted)' }}>
                      Rule: <code>{f.rule_code}</code>
                      {f.tradeline_id && <> · Tradeline #{f.tradeline_id}</>}
                    </div>
                  </div>
                ))}
              </div>
            );
          })
        )}
      </main>
    </div>
  );
}
