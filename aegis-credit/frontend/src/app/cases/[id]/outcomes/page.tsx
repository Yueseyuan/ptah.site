'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listOutcomes, createOutcome, updateOutcome, deleteOutcome } from '@/lib/api';

interface Outcome { id: number; outcome_type: string; description: string; bureau: string; achieved_date: string; verified: boolean; score_before: number | null; score_after: number | null; created_at: string; }

const OUTCOME_TYPES = ['deleted', 'updated', 'score_increase', 'letter_sent', 'goodwill_approved', 'judgment_vacated', 'other'];

export default function OutcomesPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ outcome_type: 'deleted', description: '', bureau: '', achieved_date: '', verified: false, score_before: '', score_after: '' });

  function load() { listOutcomes(caseId).then(setOutcomes).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = { case_id: caseId, outcome_type: form.outcome_type, description: form.description, bureau: form.bureau, achieved_date: form.achieved_date, verified: form.verified };
    if (form.score_before) payload.score_before = parseInt(form.score_before);
    if (form.score_after) payload.score_after = parseInt(form.score_after);
    await createOutcome(payload);
    setShowForm(false);
    setForm({ outcome_type: 'deleted', description: '', bureau: '', achieved_date: '', verified: false, score_before: '', score_after: '' });
    load();
  }

  async function verify(outcomeId: number, v: boolean) {
    await updateOutcome(outcomeId, { verified: v });
    load();
  }

  async function del(outcomeId: number) {
    if (!confirm('Delete this outcome?')) return;
    await deleteOutcome(outcomeId);
    load();
  }

  const totalScoreGain = outcomes.reduce((s, o) => s + ((o.score_after ?? 0) - (o.score_before ?? 0)), 0);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Outcomes</h1><p>Track verified results and credit score improvements</p></div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Log Outcome'}</button>
        </div>
        <CaseNav caseId={caseId} />

        <div className="stat-grid" style={{ marginBottom: 16 }}>
          <div className="stat-card"><div className="label">Total Outcomes</div><div className="value">{outcomes.length}</div></div>
          <div className="stat-card"><div className="label">Verified</div><div className="value" style={{ color: 'var(--success)' }}>{outcomes.filter(o => o.verified).length}</div></div>
          <div className="stat-card"><div className="label">Deletions</div><div className="value">{outcomes.filter(o => o.outcome_type === 'deleted').length}</div></div>
          <div className="stat-card"><div className="label">Score Gain</div><div className="value" style={{ color: totalScoreGain > 0 ? 'var(--success)' : 'inherit' }}>{totalScoreGain > 0 ? `+${totalScoreGain}` : totalScoreGain}</div></div>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Log Outcome</h3>
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group"><label>Outcome Type *</label><select value={form.outcome_type} onChange={e => setForm(f => ({ ...f, outcome_type: e.target.value }))}>
                  {OUTCOME_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </select></div>
                <div className="form-group"><label>Bureau</label><input value={form.bureau} onChange={e => setForm(f => ({ ...f, bureau: e.target.value }))} placeholder="experian / equifax / transunion" /></div>
                <div className="form-group"><label>Achieved Date</label><input type="date" value={form.achieved_date} onChange={e => setForm(f => ({ ...f, achieved_date: e.target.value }))} /></div>
                <div className="form-group" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
                  <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 400 }}>
                    <input type="checkbox" checked={form.verified} onChange={e => setForm(f => ({ ...f, verified: e.target.checked }))} style={{ width: 'auto' }} />
                    Verified / Confirmed
                  </label>
                </div>
                <div className="form-group"><label>Score Before</label><input type="number" value={form.score_before} onChange={e => setForm(f => ({ ...f, score_before: e.target.value }))} /></div>
                <div className="form-group"><label>Score After</label><input type="number" value={form.score_after} onChange={e => setForm(f => ({ ...f, score_after: e.target.value }))} /></div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}><label>Description</label><textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">Save Outcome</button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? <div className="spinner" /> : outcomes.length === 0 ? (
            <p className="empty">No outcomes logged yet.</p>
          ) : (
            <table>
              <thead><tr><th>Type</th><th>Bureau</th><th>Description</th><th>Score Change</th><th>Date</th><th>Verified</th><th></th></tr></thead>
              <tbody>
                {outcomes.map(o => (
                  <tr key={o.id}>
                    <td><span className="badge badge-success">{o.outcome_type.replace(/_/g, ' ')}</span></td>
                    <td style={{ textTransform: 'capitalize' }}>{o.bureau || '—'}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{o.description || '—'}</td>
                    <td>
                      {o.score_before && o.score_after ? (
                        <span style={{ color: o.score_after > o.score_before ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                          {o.score_before} → {o.score_after} ({o.score_after - o.score_before > 0 ? '+' : ''}{o.score_after - o.score_before})
                        </span>
                      ) : '—'}
                    </td>
                    <td style={{ fontSize: 12 }}>{o.achieved_date || '—'}</td>
                    <td>
                      <input type="checkbox" checked={o.verified} onChange={e => verify(o.id, e.target.checked)} style={{ width: 'auto' }} />
                    </td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => del(o.id)}>×</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
