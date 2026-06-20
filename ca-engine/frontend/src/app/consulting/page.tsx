'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listConsultingEngagements, createConsultingEngagement, listClients } from '@/lib/api';

interface Engagement {
  id: number;
  engagement_number: string;
  client_id: number;
  status: string;
  engagement_type: string;
  business_stage: string;
  business_type: string;
  total_fee: number;
  session_datetime: string | null;
  created_at: string;
}

interface Client { id: number; first_name: string; last_name: string; }

const TYPES = [
  { value: 'hourly', label: 'Hourly — $150/hr' },
  { value: 'package', label: 'Package — $500' },
  { value: 'retainer', label: 'Retainer' },
];
const STAGES = ['idea', 'startup', 'early', 'growth', 'acquisition'];

const blank = {
  client_id: '', engagement_type: 'hourly', business_stage: 'startup',
  business_type: '', session_datetime: '', notes: '',
};

export default function ConsultingPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [e, c] = await Promise.all([listConsultingEngagements(), listClients()]);
      setEngagements(e);
      setClients(c);
    } catch { /* backend offline */ }
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload: Record<string, unknown> = {
        client_id: Number(form.client_id),
        engagement_type: form.engagement_type,
        business_stage: form.business_stage,
      };
      if (form.business_type) payload.business_type = form.business_type;
      if (form.session_datetime) payload.session_datetime = form.session_datetime;
      if (form.notes) payload.notes = form.notes;
      await createConsultingEngagement(payload);
      setForm(blank);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      setErr(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message || 'Failed to create engagement.');
    } finally {
      setSaving(false);
    }
  }

  const clientName = (id: number) => {
    const c = clients.find(c => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : `#${id}`;
  };

  const totalBilled = engagements.reduce((s, e) => s + (e.total_fee ?? 0), 0);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Division 6 — Business Consulting</h1>
            <p>LLC/Corp startup, SOPs, business plans, strategy. $150/hr or $500 package.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Cancel' : '+ New Engagement'}
          </button>
        </div>

        <div className="stat-grid" style={{ marginBottom: 24 }}>
          <div className="stat-card">
            <div className="label">Total Engagements</div>
            <div className="value">{engagements.length}</div>
          </div>
          <div className="stat-card">
            <div className="label">Active</div>
            <div className="value">{engagements.filter(e => ['active', 'scheduled'].includes(e.status)).length}</div>
          </div>
          <div className="stat-card">
            <div className="label">Total Billed</div>
            <div className="value">${totalBilled.toFixed(2)}</div>
          </div>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Schedule Consulting Engagement</h3>
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
                  <label>Engagement Type *</label>
                  <select value={form.engagement_type} onChange={e => setForm(f => ({ ...f, engagement_type: e.target.value }))}>
                    {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Business Stage</label>
                  <select value={form.business_stage} onChange={e => setForm(f => ({ ...f, business_stage: e.target.value }))}>
                    {STAGES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Business Type</label>
                  <input value={form.business_type} placeholder="LLC, Corp, Sole Prop…"
                    onChange={e => setForm(f => ({ ...f, business_type: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Session Date/Time</label>
                  <input type="datetime-local" value={form.session_datetime}
                    onChange={e => setForm(f => ({ ...f, session_datetime: e.target.value }))} />
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Notes / Goals</label>
                  <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={3} />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Scheduling…' : 'Schedule Engagement'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Engagement #</th>
                <th>Client</th>
                <th>Type</th>
                <th>Stage</th>
                <th>Status</th>
                <th>Fee</th>
                <th>Session</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {engagements.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>No engagements yet.</td></tr>
              )}
              {engagements.map(e => (
                <tr key={e.id}>
                  <td><code>{e.engagement_number}</code></td>
                  <td>{clientName(e.client_id)}</td>
                  <td>{e.engagement_type}</td>
                  <td>{e.business_stage}</td>
                  <td><span className={`badge badge-${e.status}`}>{e.status}</span></td>
                  <td>${e.total_fee}</td>
                  <td>{e.session_datetime ? new Date(e.session_datetime).toLocaleString() : '—'}</td>
                  <td>{new Date(e.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
