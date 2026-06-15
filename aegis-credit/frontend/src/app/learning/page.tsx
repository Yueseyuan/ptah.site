'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listLearning, createLearningEntry, deleteLearningEntry } from '@/lib/api';

interface Entry { id: number; bureau: string; creditor_name: string; tactic_used: string; fcra_basis: string; outcome: string; notes: string; created_at: string; }

const OUTCOMES = ['success', 'partial', 'failure'];
const BUREAUS = ['experian', 'equifax', 'transunion', 'innovis', 'all'];

export default function LearningPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState({ bureau: '', outcome: '' });
  const [form, setForm] = useState({ bureau: '', creditor_name: '', tactic_used: '', fcra_basis: '', outcome: 'success', notes: '' });

  function load() { listLearning(filter.bureau || filter.outcome ? { bureau: filter.bureau || undefined, outcome: filter.outcome || undefined } : undefined).then(setEntries).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [filter]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await createLearningEntry(form);
    setShowForm(false);
    setForm({ bureau: '', creditor_name: '', tactic_used: '', fcra_basis: '', outcome: 'success', notes: '' });
    load();
  }

  async function del(entryId: number) {
    if (!confirm('Delete this entry?')) return;
    await deleteLearningEntry(entryId);
    load();
  }

  const outcomeColor: Record<string, string> = { success: 'badge-success', partial: 'badge-medium', failure: 'badge-high' };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Learning Vault</h1><p>Track what tactics work — build institutional knowledge over time</p></div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Entry'}</button>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <select value={filter.bureau} onChange={e => setFilter(f => ({ ...f, bureau: e.target.value }))}
            style={{ padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}>
            <option value="">All Bureaus</option>
            {BUREAUS.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
          <select value={filter.outcome} onChange={e => setFilter(f => ({ ...f, outcome: e.target.value }))}
            style={{ padding: '6px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}>
            <option value="">All Outcomes</option>
            {OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add Learning Entry</h3>
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group"><label>Bureau</label><select value={form.bureau} onChange={e => setForm(f => ({ ...f, bureau: e.target.value }))}>
                  <option value="">Any</option>
                  {BUREAUS.map(b => <option key={b} value={b}>{b}</option>)}
                </select></div>
                <div className="form-group"><label>Creditor Name</label><input value={form.creditor_name} onChange={e => setForm(f => ({ ...f, creditor_name: e.target.value }))} /></div>
                <div className="form-group"><label>Tactic Used *</label><input required value={form.tactic_used} onChange={e => setForm(f => ({ ...f, tactic_used: e.target.value }))} placeholder="e.g., Debt validation letter, Goodwill letter" /></div>
                <div className="form-group"><label>FCRA Basis</label><input value={form.fcra_basis} onChange={e => setForm(f => ({ ...f, fcra_basis: e.target.value }))} placeholder="e.g., FCRA §609, §611" /></div>
                <div className="form-group"><label>Outcome *</label><select value={form.outcome} onChange={e => setForm(f => ({ ...f, outcome: e.target.value }))}>
                  {OUTCOMES.map(o => <option key={o} value={o}>{o}</option>)}
                </select></div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}><label>Notes</label><textarea rows={3} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="What worked, what didn't, timeline, response details…" /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">Save Entry</button>
            </form>
          </div>
        )}

        <div className="card">
          <h3>Entries ({entries.length})</h3>
          {loading ? <div className="spinner" /> : entries.length === 0 ? (
            <p className="empty">No entries yet. Start logging what tactics work.</p>
          ) : (
            <table>
              <thead><tr><th>Outcome</th><th>Bureau</th><th>Creditor</th><th>Tactic</th><th>FCRA</th><th>Notes</th><th>Date</th><th></th></tr></thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.id}>
                    <td><span className={`badge ${outcomeColor[e.outcome] || 'badge-pending'}`}>{e.outcome}</span></td>
                    <td style={{ textTransform: 'capitalize' }}>{e.bureau || 'any'}</td>
                    <td>{e.creditor_name || '—'}</td>
                    <td>{e.tactic_used}</td>
                    <td><code style={{ fontSize: 11 }}>{e.fcra_basis || '—'}</code></td>
                    <td style={{ fontSize: 12, color: 'var(--muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.notes}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(e.created_at).toLocaleDateString()}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => del(e.id)}>×</button></td>
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
