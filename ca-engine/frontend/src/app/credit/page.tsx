'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
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
  first_work_completed: boolean;
  created_at: string;
}

interface Client { id: number; first_name: string; last_name: string; }

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
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      setErr(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message || 'Failed to create case.');
    } finally {
      setSaving(false);
    }
  }

  const clientName = (id: number) => {
    const c = clients.find(c => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : `#${id}`;
  };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Division 2 — Credit Restoration</h1>
            <p>CSO Compliance: billing only AFTER first work completed. FCRA dispute tracking per bureau.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Cancel' : '+ New Case'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Open Credit Restoration Case</h3>
            {err && <div className="alert-error">{err}</div>}
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Client *</label>
                  <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                    <option value="">Select client…</option>
                    {clients.map(c => <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Notes</label>
                  <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                    placeholder="Initial intake notes…" />
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
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Opening…' : 'Open Case'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          <table>
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
                <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>No credit cases yet.</td></tr>
              )}
              {cases.map(c => (
                <tr key={c.id}>
                  <td><code>{c.case_number}</code></td>
                  <td>{clientName(c.client_id)}</td>
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
      </main>
    </div>
  );
}
