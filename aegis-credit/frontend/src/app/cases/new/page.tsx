'use client';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { createCase, listClients } from '@/lib/api';

interface Client { id: number; first_name: string; last_name: string; }

function NewCaseForm() {
  const router = useRouter();
  const params = useSearchParams();
  const preselect = params.get('client_id') || '';
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState({ client_id: preselect, goal: '', notes: '', assigned_to: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { listClients().then(setClients); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.client_id) { setError('Select a client.'); return; }
    setLoading(true);
    setError('');
    try {
      const c = await createCase({ client_id: parseInt(form.client_id), goal: form.goal, notes: form.notes, assigned_to: form.assigned_to });
      router.push(`/cases/${c.id}`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : d ? JSON.stringify(d) : e.message || 'Failed to create case.');
    } finally { setLoading(false); }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header"><h1>New Case</h1><p>Open a new credit investigation case</p></div>
        <form onSubmit={submit} style={{ maxWidth: 600 }}>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Case Setup</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Client *</label>
                <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">— Select Client —</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Assigned To</label>
                <input value={form.assigned_to} onChange={e => setForm(f => ({ ...f, assigned_to: e.target.value }))} placeholder="Staff member (optional)" />
              </div>
            </div>
            <div className="form-group">
              <label>Client Goal</label>
              <input value={form.goal} onChange={e => setForm(f => ({ ...f, goal: e.target.value }))} placeholder="e.g., Qualify for mortgage, Remove collections, Improve score" />
            </div>
            <div className="form-group">
              <label>Notes</label>
              <textarea rows={3} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Internal case notes…" />
            </div>
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Creating…' : 'Create Case'}</button>
            <button type="button" className="btn btn-outline" onClick={() => router.back()}>Cancel</button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default function NewCasePage() {
  return (
    <Suspense fallback={<div className="main-layout"><main style={{ padding: 40 }}><div className="spinner" /></main></div>}>
      <NewCaseForm />
    </Suspense>
  );
}
