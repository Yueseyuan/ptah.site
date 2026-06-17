'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listFindings, generateFindings, updateFinding, approveFinding, listDisputeRounds, addFindingToDispute } from '@/lib/api';

interface Finding { id: number; finding_type: string; severity: string; title: string; description: string; fcra_section: string; requires_human_review: boolean; status: string; tradeline_id?: number; }
interface Round { id: number; round_number: number; bureau: string; status: string; }

const SEV_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2, info: 3 };
const SEV_COLOR: Record<string, string> = { high: '#fee2e2', medium: '#fef3c7', low: '#dbeafe', info: '#f3f4f6' };
const SEV_TEXT: Record<string, string> = { high: '#991b1b', medium: '#92400e', low: '#1e40af', info: '#374151' };

const STATUS_BADGE: Record<string, { bg: string; color: string }> = {
  open: { bg: '#fef3c7', color: '#92400e' },
  reviewed: { bg: '#dcfce7', color: '#166534' },
  in_dispute: { bg: '#dbeafe', color: '#1e40af' },
  closed: { bg: '#f3f4f6', color: '#6b7280' },
};

export default function FindingsPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [disputeForm, setDisputeForm] = useState<{ findingId: number; roundId: string } | null>(null);
  const [filterType, setFilterType] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  function load() {
    Promise.all([
      listFindings(caseId),
      listDisputeRounds(caseId),
    ]).then(([f, r]) => {
      setFindings(f.sort((a: Finding, b: Finding) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9)));
      setRounds(r);
    }).finally(() => setLoading(false));
  }
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
      setError(typeof d === 'string' ? d : e.message || 'Generation failed.');
    } finally { setGenerating(false); }
  }

  async function approve(findingId: number) {
    await approveFinding(findingId, 'Approved by investigator');
    load();
  }

  async function submitToDispute() {
    if (!disputeForm || !disputeForm.roundId) return;
    try {
      await addFindingToDispute(disputeForm.findingId, parseInt(disputeForm.roundId));
      setSuccess('Finding added to dispute round.');
      setDisputeForm(null);
      load();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Failed to add to dispute.');
    }
  }

  const allTypes = Array.from(new Set(findings.map(f => f.finding_type))).sort();
  const displayed = findings.filter(f =>
    (!filterType || f.finding_type === filterType) &&
    (!filterSeverity || f.severity === filterSeverity) &&
    (!filterStatus || f.status === filterStatus)
  );

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Findings</h1><p>{findings.length} total · {displayed.length} shown</p></div>
          <button className="btn btn-primary" onClick={generate} disabled={generating}>
            {generating ? 'Generating…' : '⚡ AI Generate Findings'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
        {success && <div className="alert alert-success" style={{ marginBottom: 12 }}>{success}</div>}

        <div className="card" style={{ marginBottom: 12, borderLeft: '3px solid #f59e0b' }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
            Human review required for all findings. This system does not provide legal advice and does not guarantee outcomes.
          </p>
        </div>

        {findings.length > 0 && (
          <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
            <select value={filterType} onChange={e => setFilterType(e.target.value)}
              style={{ fontSize: 12, padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
              <option value="">All Types</option>
              {allTypes.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
            <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
              style={{ fontSize: 12, padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
              <option value="">All Severities</option>
              {['high', 'medium', 'low', 'info'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
              style={{ fontSize: 12, padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
              <option value="">All Statuses</option>
              {['open', 'reviewed', 'in_dispute', 'closed'].map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
            </select>
            {(filterType || filterSeverity || filterStatus) && (
              <button onClick={() => { setFilterType(''); setFilterSeverity(''); setFilterStatus(''); }}
                className="btn btn-outline" style={{ fontSize: 12, padding: '6px 10px' }}>Clear Filters</button>
            )}
          </div>
        )}

        {loading ? <div className="spinner" /> : displayed.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
            {findings.length === 0
              ? 'No findings yet. Run AI Generate or analyze specific engines from their tabs.'
              : 'No findings match the current filters.'}
          </div>
        ) : (
          <div>
            {displayed.map(f => {
              const sb = STATUS_BADGE[f.status] || STATUS_BADGE.open;
              return (
                <div key={f.id} className="card" style={{ marginBottom: 10, borderLeft: `4px solid ${SEV_TEXT[f.severity] || '#6b7280'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
                        <span style={{ background: SEV_COLOR[f.severity], color: SEV_TEXT[f.severity], borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' }}>
                          {f.severity}
                        </span>
                        <span style={{ background: sb.bg, color: sb.color, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 500 }}>
                          {f.status.replace('_', ' ')}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{f.finding_type}</span>
                        {f.requires_human_review && f.status === 'open' && (
                          <span style={{ background: '#fef9c3', color: '#713f12', borderRadius: 4, padding: '2px 8px', fontSize: 10, fontWeight: 600 }}>
                            ⚠ HUMAN REVIEW REQUIRED
                          </span>
                        )}
                      </div>
                      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{f.title}</div>
                      {f.description && <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>{f.description}</div>}
                      {f.fcra_section && <div style={{ fontSize: 11, color: '#6366f1', fontWeight: 500 }}>{f.fcra_section}</div>}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 140, alignItems: 'flex-end' }}>
                      {f.status === 'open' && (
                        <button onClick={() => approve(f.id)} className="btn" style={{ fontSize: 12, padding: '4px 10px', background: '#dcfce7', color: '#166534', border: 'none' }}>
                          ✓ Approve
                        </button>
                      )}
                      {f.status !== 'in_dispute' && rounds.length > 0 && (
                        <button onClick={() => setDisputeForm({ findingId: f.id, roundId: String(rounds[0]?.id || '') })} className="btn" style={{ fontSize: 12, padding: '4px 10px', background: '#dbeafe', color: '#1e40af', border: 'none' }}>
                          + Add to Dispute
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Inline dispute form */}
                  {disputeForm?.findingId === f.id && (
                    <div style={{ marginTop: 10, padding: '10px 12px', background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0', display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Add to round:</span>
                      <select value={disputeForm.roundId} onChange={e => setDisputeForm(d => d ? { ...d, roundId: e.target.value } : d)}
                        style={{ fontSize: 12, padding: '4px 8px', borderRadius: 4, border: '1px solid var(--border)' }}>
                        {rounds.map(r => (
                          <option key={r.id} value={r.id}>Round {r.round_number} — {r.bureau} ({r.status})</option>
                        ))}
                      </select>
                      <button onClick={submitToDispute} className="btn btn-primary" style={{ fontSize: 12, padding: '4px 10px' }}>Add</button>
                      <button onClick={() => setDisputeForm(null)} className="btn" style={{ fontSize: 12, padding: '4px 10px' }}>Cancel</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
