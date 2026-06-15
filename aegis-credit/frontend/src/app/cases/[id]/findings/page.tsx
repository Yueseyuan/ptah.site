'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listFindings, generateFindings, updateFinding } from '@/lib/api';

interface Finding { id: number; finding_type: string; severity: string; title: string; description: string; fcra_section: string; requires_human_review: boolean; status: string; tradeline_id?: number; }

const SEV_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2, info: 3 };

export default function FindingsPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() { listFindings(caseId).then(f => setFindings(f.sort((a: Finding, b: Finding) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9)))).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function generate() {
    setGenerating(true); setError(''); setSuccess('');
    try {
      const r = await generateFindings(caseId);
      setSuccess(`Generated ${r.findings_generated} findings.`);
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Generation failed. Make sure ANTHROPIC_API_KEY is configured and tradelines are parsed.');
    } finally { setGenerating(false); }
  }

  async function markStatus(findingId: number, status: string) {
    await updateFinding(findingId, { status });
    load();
  }

  const sevColor: Record<string, string> = { high: '#fee2e2', medium: '#fef3c7', low: '#dbeafe', info: '#f3f4f6' };
  const sevText: Record<string, string> = { high: '#991b1b', medium: '#92400e', low: '#1e40af', info: '#374151' };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Findings</h1><p>AI-identified issues, discrepancies, and FCRA concerns</p></div>
          <button className="btn btn-primary" onClick={generate} disabled={generating}>{generating ? 'Generating…' : '⚡ Generate Findings'}</button>
        </div>
        <CaseNav caseId={caseId} />

        <div className="disclosure-banner">
          All findings are preliminary and require human review before any action is taken. No finding constitutes a proven violation, legal advice, or a guarantee of any outcome.
        </div>

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        {loading ? <div className="spinner" /> : findings.length === 0 ? (
          <div className="card"><p className="empty">No findings yet. Upload credit reports, run comparison, then generate findings.</p></div>
        ) : (
          findings.map(f => (
            <div key={f.id} className="card" style={{ marginBottom: 12, borderLeft: `4px solid ${f.severity === 'high' ? 'var(--danger)' : f.severity === 'medium' ? 'var(--warning)' : 'var(--info)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ background: sevColor[f.severity], color: sevText[f.severity], padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>{f.severity.toUpperCase()}</span>
                  <span style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{f.finding_type}</span>
                  {f.fcra_section && <code style={{ fontSize: 11 }}>{f.fcra_section}</code>}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <select value={f.status} onChange={e => markStatus(f.id, e.target.value)}
                    style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, border: '1px solid var(--border)' }}>
                    <option value="open">Open</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="actioned">Actioned</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </div>
              </div>
              <h4 style={{ marginBottom: 6, color: 'var(--navy)' }}>{f.title}</h4>
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>{f.description}</p>
              {f.requires_human_review && (
                <span className="review-flag">⚠ Requires human review before any action</span>
              )}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
