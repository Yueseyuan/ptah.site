'use client';
import { useEffect, useState } from 'react';
import { listReliefCases, createReliefCase, listClients } from '@/lib/api';

interface ReliefCase {
  id: number;
  case_number: string;
  client_id: number;
  status: string;
  service_tier: string;
  needs_attorney: boolean;
  referral_reason: string | null;
  referral_sent: boolean;
  target_employer: string;
  target_landlord: string;
  notes: string;
  created_at: string;
}

interface Client { id: number; full_name: string; }

const TIERS = [
  { value: 'basic', label: 'Basic — $150 (Letter Package)' },
  { value: 'standard', label: 'Standard — $250 (Letter + Follow-up)' },
  { value: 'premium', label: 'Premium — $350 (Full Support, Attorney Referral)' },
];

const blank = { client_id: '', service_tier: 'standard', target_employer: '', target_landlord: '', notes: '' };

export default function ReliefPage() {
  const [cases, setCases] = useState<ReliefCase[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [r, c] = await Promise.all([listReliefCases(), listClients()]);
      setCases(r);
      setClients(c);
    } catch { /* backend offline */ }
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''));
      if (payload.client_id) payload.client_id = Number(payload.client_id) as unknown as string;
      await createReliefCase(payload);
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
      <div className="card" style={{ marginBottom: 16, background: '#fff3cd', borderColor: '#ffc107' }}>
        <strong>DISCLOSURE:</strong> Cruel &amp; Associates is not a law firm and does not provide legal advice or
        legal representation. We are not attorneys. Criminal Relief services consist of administrative
        document assistance only. Any legal services are provided exclusively by licensed attorneys.
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Division 3 — Criminal Relief</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            Background mitigation letters, rehabilitation narratives, employer/landlord advocacy.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(s => !s)}>
          {showForm ? 'Cancel' : '+ New Case'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Open Relief Case</h3>
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
                <label>Service Tier *</label>
                <select value={form.service_tier} onChange={e => setForm(f => ({ ...f, service_tier: e.target.value }))}>
                  {TIERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Target Employer</label>
                <input value={form.target_employer} onChange={e => setForm(f => ({ ...f, target_employer: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Target Landlord</label>
                <input value={form.target_landlord} onChange={e => setForm(f => ({ ...f, target_landlord: e.target.value }))} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes / Offense Summary</label>
                <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={3} />
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
              <th>Tier</th>
              <th>Status</th>
              <th>Atty Referral</th>
              <th>Employer</th>
              <th>Landlord</th>
              <th>Opened</th>
            </tr>
          </thead>
          <tbody>
            {cases.length === 0 && (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--muted)' }}>No relief cases yet.</td></tr>
            )}
            {cases.map(c => (
              <tr key={c.id}>
                <td><code>{c.case_number}</code></td>
                <td>{clients.find(cl => cl.id === c.client_id)?.full_name ?? `#${c.client_id}`}</td>
                <td>{c.service_tier}</td>
                <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                <td>{c.needs_attorney ? <span style={{ color: '#e74c3c' }}>Required</span> : '—'}</td>
                <td>{c.target_employer || '—'}</td>
                <td>{c.target_landlord || '—'}</td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
