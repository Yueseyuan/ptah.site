'use client';
import { useEffect, useState } from 'react';
import { listNotaryJobs, createNotaryJob, listClients, updateNotaryJobStatus } from '@/lib/api';

interface NotaryJob {
  id: number;
  job_number: string;
  client_id: number;
  job_type: string;
  status: string;
  fee: number;
  scheduled_at: string | null;
  signer_name: string;
  signer_address: string;
  notes: string;
  created_at: string;
}

interface Client { id: number; full_name: string; }

const JOB_TYPES = [
  { value: 'loan_signing', label: 'Loan Signing', fee: 150 },
  { value: 'real_estate', label: 'Real Estate', fee: 125 },
  { value: 'general_notary', label: 'General Notary', fee: 75 },
  { value: 'ron', label: 'Remote Online (RON)', fee: 100 },
];

const blank = {
  client_id: '', job_type: 'loan_signing', signer_name: '',
  signer_address: '', scheduled_at: '', notes: '',
};

export default function NotaryJobsPage() {
  const [jobs, setJobs] = useState<NotaryJob[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [j, c] = await Promise.all([listNotaryJobs(), listClients()]);
      setJobs(j);
      setClients(c);
    } catch { /* backend may be offline */ }
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v !== '')
      );
      if (payload.client_id) payload.client_id = Number(payload.client_id) as unknown as string;
      await createNotaryJob(payload);
      setForm(blank);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setErr(err.response?.data?.detail || err.message || 'Failed to create job.');
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(id: number, status: string) {
    try { await updateNotaryJobStatus(id, status); await load(); } catch { /* ignore */ }
  }

  const fee = JOB_TYPES.find(t => t.value === form.job_type)?.fee ?? 0;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Division 1 — Notary Jobs</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            SC §26-1-120 fee cap $5.00/act enforced. Loan signing $150 · Real estate $125 · General $75 · RON $100
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(s => !s)}>
          {showForm ? 'Cancel' : '+ New Job'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Schedule Notary Job</h3>
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
                <label>Job Type *</label>
                <select value={form.job_type} onChange={e => setForm(f => ({ ...f, job_type: e.target.value }))} required>
                  {JOB_TYPES.map(t => <option key={t.value} value={t.value}>{t.label} (${t.fee})</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Signer Name *</label>
                <input value={form.signer_name} onChange={e => setForm(f => ({ ...f, signer_name: e.target.value }))} required />
              </div>
              <div className="form-group">
                <label>Scheduled At</label>
                <input type="datetime-local" value={form.scheduled_at} onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Signer Address</label>
                <input value={form.signer_address} onChange={e => setForm(f => ({ ...f, signer_address: e.target.value }))} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>Notes</label>
                <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
              </div>
            </div>
            <div style={{ marginTop: 12, color: 'var(--muted)', fontSize: 13 }}>
              Estimated fee: <strong>${fee}</strong>
            </div>
            <div style={{ marginTop: 16 }}>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Scheduling…' : 'Schedule Job'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Job #</th>
              <th>Client</th>
              <th>Type</th>
              <th>Signer</th>
              <th>Fee</th>
              <th>Status</th>
              <th>Scheduled</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--muted)' }}>No notary jobs yet.</td></tr>
            )}
            {jobs.map(j => (
              <tr key={j.id}>
                <td><code>{j.job_number}</code></td>
                <td>{clients.find(c => c.id === j.client_id)?.full_name ?? `#${j.client_id}`}</td>
                <td>{JOB_TYPES.find(t => t.value === j.job_type)?.label ?? j.job_type}</td>
                <td>{j.signer_name}</td>
                <td>${j.fee}</td>
                <td><span className={`badge badge-${j.status}`}>{j.status}</span></td>
                <td>{j.scheduled_at ? new Date(j.scheduled_at).toLocaleString() : '—'}</td>
                <td>
                  {j.status === 'scheduled' && (
                    <button className="btn-sm" onClick={() => changeStatus(j.id, 'completed')}>
                      Complete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
