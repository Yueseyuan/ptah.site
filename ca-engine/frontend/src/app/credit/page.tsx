'use client';
import { useEffect, useState } from 'react';
import { listCreditCases, createCreditCase, listClients } from '@/lib/api';

interface CreditCase {
  id: number;
  case_number: string;
  client_id: number;
  status: string;
  starting_score_eq: number | null;
  starting_score_ex: number | null;
  starting_score_tu: number | null;
  current_score_eq: number | null;
  current_score_ex: number | null;
  current_score_tu: number | null;
  total_negative_items: number;
  items_removed: number;
  items_in_dispute: number;
  first_work_completed: boolean;
  notes: string;
  created_at: string;
}

interface Client { id: number; full_name: string; }

const blank = { client_id: '', starting_score_eq: '', starting_score_ex: '', starting_score_tu: '', notes: '' };

export default function CreditPage() {
  const [cases, setCases] = useState<CreditCase[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [c, cl] = await Promise.all([listCreditCases(), listClients()]);
      setCases(c);
      setClients(cl);
    } catch { /* backend offline */ }
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload: Record<string, unknown> = { client_id: Number(form.client_id) };
      if (form.starting_score_eq) payload.starting_score_eq = Number(form.starting_score_eq);
      if (form.starting_score_ex) payload.starting_score_ex = Number(form.starting_score_ex);
      if (form.starting_score_tu) payload.starting_score_tu = Number(form.starting_score_tu);
      if (form.notes) payload.notes = form.notes;
      await createCreditCase(payload);
      setForm(blank);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setErr(err.response?.data?.detail || err.message || 'Failed to create case.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Division 2 — Credit Restoration</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            CSO Compliance: billing only AFTER first work completed. FCRA dispute tracking per bureau.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(s => !s)}>
          {showForm ? 'Cancel' : '+ New Case'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Open Credit Restoration Case</h3>
          {err && <div className="alert-error">{err}</div>}
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="form-group">
                <label>Client *</label>
                <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">Select client…</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Starting Score — Equifax</label>
                <input type="number" min={300} max={850} value={form.starting_score_eq}
                  onChange={e => setForm(f => ({ ...f, starting_score_eq: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Starting Score — Experian</label>
                <input type="number" min={300} max={850} value={form.starting_score_ex}
                  onChange={e => setForm(f => ({ ...f, starting_score_ex: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Starting Score — TransUnion</label>
                <input type="number" min={300} max={850} value={form.starting_score_tu}
                  onChange={e => setForm(f => ({ ...f, starting_score_tu: e.target.value }))} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Opening…' : 'Open Case'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Case #</th>
              <th>Client</th>
              <th>Status</th>
              <th>EQ / EX / TU (Start)</th>
              <th>EQ / EX / TU (Now)</th>
              <th>Items</th>
              <th>Removed</th>
              <th>First Work</th>
              <th>Opened</th>
            </tr>
          </thead>
          <tbody>
            {cases.length === 0 && (
              <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--muted)' }}>No credit cases yet.</td></tr>
            )}
            {cases.map(c => (
              <tr key={c.id}>
                <td><code>{c.case_number}</code></td>
                <td>{clients.find(cl => cl.id === c.client_id)?.full_name ?? `#${c.client_id}`}</td>
                <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                <td>{c.starting_score_eq ?? '—'} / {c.starting_score_ex ?? '—'} / {c.starting_score_tu ?? '—'}</td>
                <td>{c.current_score_eq ?? '—'} / {c.current_score_ex ?? '—'} / {c.current_score_tu ?? '—'}</td>
                <td>{c.total_negative_items ?? 0}</td>
                <td>{c.items_removed ?? 0}</td>
                <td>{c.first_work_completed ? '✓' : '—'}</td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
