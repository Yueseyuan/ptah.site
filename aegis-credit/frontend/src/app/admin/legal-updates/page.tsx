'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listLegalUpdates, submitLegalUpdate, approveLegalUpdate, rejectLegalUpdate } from '@/lib/api';

interface LegalUpdate {
  id: number;
  update_type: string;
  title: string;
  source_url: string | null;
  summary: string | null;
  proposed_changes: string | null;
  status: 'pending' | 'approved' | 'rejected';
  submitted_by: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string | null;
}

const STATUS_STYLE: Record<string, { bg: string; color: string }> = {
  pending: { bg: '#fef3c7', color: '#92400e' },
  approved: { bg: '#dcfce7', color: '#166534' },
  rejected: { bg: '#fee2e2', color: '#991b1b' },
};

const UPDATE_TYPES = ['federal', 'guidance', 'state', 'case_law'];

export default function LegalUpdatesPage() {
  const [updates, setUpdates] = useState<LegalUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [working, setWorking] = useState<number | null>(null);
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectNotes, setRejectNotes] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [form, setForm] = useState({
    update_type: 'federal',
    title: '',
    source_url: '',
    summary: '',
    proposed_changes: '',
    submitted_by: '',
  });

  function load() {
    listLegalUpdates().then(setUpdates).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      await submitLegalUpdate({ ...form, source_url: form.source_url || null, submitted_by: form.submitted_by || null });
      setSuccess('Update submitted for review.');
      setShowForm(false);
      setForm({ update_type: 'federal', title: '', source_url: '', summary: '', proposed_changes: '', submitted_by: '' });
      load();
    } catch {
      setError('Failed to submit update.');
    }
  }

  async function handleApprove(id: number) {
    setWorking(id); setError(''); setSuccess('');
    try {
      await approveLegalUpdate(id);
      setSuccess('Update approved and applied to legal database.');
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Approval failed.');
    } finally { setWorking(null); }
  }

  async function handleReject(id: number) {
    setWorking(id); setError(''); setSuccess('');
    try {
      await rejectLegalUpdate(id, rejectNotes);
      setSuccess('Update rejected.');
      setRejectId(null); setRejectNotes('');
      load();
    } catch {
      setError('Rejection failed.');
    } finally { setWorking(null); }
  }

  const visible = filterStatus ? updates.filter(u => u.status === filterStatus) : updates;
  const pendingCount = updates.filter(u => u.status === 'pending').length;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Legal Database Updates</h1>
            <p>Review and approve changes to the legal knowledge base{pendingCount > 0 ? ` · ${pendingCount} pending` : ''}</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Submit Update'}</button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
        {success && <div className="alert alert-success" style={{ marginBottom: 12 }}>{success}</div>}

        {showForm && (
          <div className="card" style={{ marginBottom: 20 }}>
            <h3>Submit New Legal Update</h3>
            <form onSubmit={handleSubmit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Update Type *</label>
                  <select value={form.update_type} onChange={e => setForm(f => ({ ...f, update_type: e.target.value }))}>
                    {UPDATE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Title *</label>
                  <input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Brief description of change" />
                </div>
                <div className="form-group">
                  <label>Source URL</label>
                  <input type="url" value={form.source_url} onChange={e => setForm(f => ({ ...f, source_url: e.target.value }))} placeholder="https://..." />
                </div>
                <div className="form-group">
                  <label>Submitted By</label>
                  <input value={form.submitted_by} onChange={e => setForm(f => ({ ...f, submitted_by: e.target.value }))} placeholder="Your name or username" />
                </div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}>
                  <label>Summary</label>
                  <textarea rows={2} value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))} placeholder="What changed and why it matters" />
                </div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}>
                  <label>Proposed Changes (JSON)</label>
                  <textarea rows={5} value={form.proposed_changes} onChange={e => setForm(f => ({ ...f, proposed_changes: e.target.value }))} placeholder={'{\n  "short_name": "FCRA",\n  "title": "Fair Credit Reporting Act",\n  "citation": "15 U.S.C. § 1681",\n  "summary": "...",\n  "category": "fcra"\n}'} style={{ fontFamily: 'monospace', fontSize: 12 }} />
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>JSON fields matching the target law table. On approval, a new record is inserted.</span>
                </div>
              </div>
              <button type="submit" className="btn btn-primary">Submit for Review</button>
            </form>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['', 'pending', 'approved', 'rejected'].map(s => (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={filterStatus === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
              {s || 'All'} {s === 'pending' && pendingCount > 0 ? `(${pendingCount})` : ''}
            </button>
          ))}
        </div>

        {loading ? <div className="spinner" /> : visible.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>
            No updates found. Submit one to propose changes to the legal database.
          </div>
        ) : (
          <div>
            {visible.map(u => {
              const ss = STATUS_STYLE[u.status] || STATUS_STYLE.pending;
              return (
                <div key={u.id} className="card" style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
                        <span style={{ background: ss.bg, color: ss.color, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>{u.status}</span>
                        <span style={{ background: '#e0e7ff', color: '#3730a3', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'capitalize' }}>{u.update_type.replace('_', ' ')}</span>
                        <span style={{ fontWeight: 600, fontSize: 14 }}>{u.title}</span>
                      </div>
                      {u.summary && <p style={{ margin: '0 0 4px', fontSize: 13, color: 'var(--muted)' }}>{u.summary}</p>}
                      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--muted)', flexWrap: 'wrap' }}>
                        {u.submitted_by && <span>By: {u.submitted_by}</span>}
                        {u.created_at && <span>Submitted: {new Date(u.created_at).toLocaleDateString()}</span>}
                        {u.reviewed_by && <span>Reviewed by: {u.reviewed_by}</span>}
                        {u.source_url && <a href={u.source_url} target="_blank" rel="noreferrer" style={{ color: '#1e40af' }}>Source ↗</a>}
                      </div>
                      {u.review_notes && (
                        <div style={{ marginTop: 8, fontSize: 12, color: '#991b1b', background: '#fef2f2', borderRadius: 4, padding: '4px 8px' }}>
                          Rejection notes: {u.review_notes}
                        </div>
                      )}
                      {u.proposed_changes && (
                        <details style={{ marginTop: 8 }}>
                          <summary style={{ fontSize: 12, color: 'var(--muted)', cursor: 'pointer' }}>View proposed changes JSON</summary>
                          <pre style={{ fontSize: 11, background: '#f8fafc', padding: 8, borderRadius: 4, marginTop: 4, overflowX: 'auto', maxHeight: 200 }}>{
                            (() => { try { return JSON.stringify(JSON.parse(u.proposed_changes), null, 2); } catch { return u.proposed_changes; } })()
                          }</pre>
                        </details>
                      )}
                    </div>
                    {u.status === 'pending' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 120, alignItems: 'flex-end' }}>
                        <button onClick={() => handleApprove(u.id)} disabled={working === u.id} className="btn" style={{ fontSize: 12, padding: '4px 12px', background: '#dcfce7', color: '#166534', border: 'none' }}>
                          ✓ Approve
                        </button>
                        {rejectId === u.id ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
                            <textarea rows={2} value={rejectNotes} onChange={e => setRejectNotes(e.target.value)} placeholder="Rejection reason…" style={{ fontSize: 11, padding: '4px 6px', borderRadius: 4, border: '1px solid var(--border)', width: 180 }} />
                            <div style={{ display: 'flex', gap: 4 }}>
                              <button onClick={() => handleReject(u.id)} disabled={working === u.id} className="btn" style={{ fontSize: 11, padding: '3px 10px', background: '#fee2e2', color: '#991b1b', border: 'none' }}>
                                Confirm
                              </button>
                              <button onClick={() => { setRejectId(null); setRejectNotes(''); }} className="btn btn-outline" style={{ fontSize: 11, padding: '3px 8px' }}>
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button onClick={() => setRejectId(u.id)} className="btn" style={{ fontSize: 12, padding: '4px 12px', background: '#fee2e2', color: '#991b1b', border: 'none' }}>
                            ✕ Reject
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
