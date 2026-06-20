'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listNotaryJobs, createNotaryJob, listClients, updateNotaryJobStatus } from '@/lib/api';

interface NotaryJob {
  id: number;
  job_number: string;
  client_id: number;
  job_type: string;
  status: string;
  total_fee: number;
  appointment_at: string | null;
  document_type: string;
  notes: string;
  created_at: string;
}

interface Client { id: number; first_name: string; last_name: string; }

const JOB_TYPES = [
  { value: 'loan_signing', label: 'Loan Signing', fee: 150 },
  { value: 'real_estate', label: 'Real Estate', fee: 125 },
  { value: 'general_notary', label: 'General Notary', fee: 75 },
  { value: 'ron', label: 'Remote Online (RON)', fee: 100 },
];

const blank = {
  client_id: '', job_type: 'loan_signing', document_type: '',
  appointment_at: '', notes: '',
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
      const payload: Record<string, unknown> = {
        client_id: Number(form.client_id),
        job_type: form.job_type,
      };
      if (form.document_type) payload.document_type = form.document_type;
      if (form.appointment_at) payload.appointment_at = form.appointment_at;
      if (form.notes) payload.notes = form.notes;
      await createNotaryJob(payload);
      setForm(blank);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      setErr(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message || 'Failed to create job.');
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(id: number, status: string) {
    try { await updateNotaryJobStatus(id, status); await load(); } catch { /* ignore */ }
  }

  const fee = JOB_TYPES.find(t => t.value === form.job_type)?.fee ?? 0;
  const clientName = (c: Client) => `${c.first_name} ${c.last_name}`;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Division 1 — Notary Jobs</h1>
            <p>SC §26-1-120 cap $5.00/act · Loan signing $150 · Real estate $125 · General $75 · RON $100</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Cancel' : '+ New Job'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Schedule Notary Job</h3>
            {err && <div className="alert-error">{err}</div>}
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Client *</label>
                  <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                    <option value="">Select client…</option>
                    {clients.map(c => <option key={c.id} value={c.id}>{clientName(c)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Job Type *</label>
                  <select value={form.job_type} onChange={e => setForm(f => ({ ...f, job_type: e.target.value }))} required>
                    {JOB_TYPES.map(t => <option key={t.value} value={t.value}>{t.label} (${t.fee})</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Document Type</label>
                  <input value={form.document_type} onChange={e => setForm(f => ({ ...f, document_type: e.target.value }))}
                    placeholder="e.g., Deed of Trust, Affidavit" />
                </div>
                <div className="form-group">
                  <label>Scheduled Date/Time</label>
                  <input type="datetime-local" value={form.appointment_at}
                    onChange={e => setForm(f => ({ ...f, appointment_at: e.target.value }))} />
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Notes</label>
                  <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
                </div>
              </div>
              <p style={{ fontSize: 13, color: 'var(--muted)', margin: '8px 0 12px' }}>
                Estimated fee: <strong>${fee}</strong>
              </p>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Scheduling…' : 'Schedule Job'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Job #</th>
                <th>Client</th>
                <th>Type</th>
                <th>Document</th>
                <th>Fee</th>
                <th>Status</th>
                <th>Scheduled</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>No notary jobs yet.</td></tr>
              )}
              {jobs.map(j => (
                <tr key={j.id}>
                  <td><code>{j.job_number}</code></td>
                  <td>{clients.find(c => c.id === j.client_id)?.first_name} {clients.find(c => c.id === j.client_id)?.last_name ?? ''}</td>
                  <td>{JOB_TYPES.find(t => t.value === j.job_type)?.label ?? j.job_type}</td>
                  <td>{j.document_type || '—'}</td>
                  <td>${j.total_fee}</td>
                  <td><span className={`badge badge-${j.status}`}>{j.status}</span></td>
                  <td>{j.appointment_at ? new Date(j.appointment_at).toLocaleString() : '—'}</td>
                  <td>
                    {j.status === 'scheduled' && (
                      <button className="btn btn-sm btn-primary" onClick={() => changeStatus(j.id, 'completed')}>
                        Complete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
