'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { createInvoice } from '@/lib/api';

const SERVICES = [
  'Notary Services', 'Credit Dispute Filing', 'Reentry Support Services',
  'Document Preparation', 'Asset Recovery Assistance', 'Business Formation',
  'Consultation', 'Other',
];

export default function NewInvoicePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    client_id: '', case_id: '', description: '', amount: '',
    due_date: '', notes: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await createInvoice({
        ...form,
        client_id: Number(form.client_id),
        case_id: form.case_id ? Number(form.case_id) : undefined,
        amount: parseFloat(form.amount),
      });
      router.push('/invoices');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create invoice.');
    } finally { setLoading(false); }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>New Invoice</h1>
          <p>Create a billing invoice for a client</p>
        </div>

        <form onSubmit={handleSubmit} style={{ maxWidth: 600 }}>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="grid-2">
              <div className="form-group">
                <label>Client ID *</label>
                <input type="number" value={form.client_id} onChange={(e) => set('client_id', e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Case ID (optional)</label>
                <input type="number" value={form.case_id} onChange={(e) => set('case_id', e.target.value)} />
              </div>
            </div>
            <div className="form-group">
              <label>Service Description *</label>
              <select value={form.description} onChange={(e) => set('description', e.target.value)} required>
                <option value="">Select service…</option>
                {SERVICES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Amount ($) *</label>
                <input type="number" step="0.01" min="0" value={form.amount}
                  onChange={(e) => set('amount', e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Due Date</label>
                <input type="date" value={form.due_date} onChange={(e) => set('due_date', e.target.value)} />
              </div>
            </div>
            <div className="form-group">
              <label>Notes</label>
              <textarea rows={3} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
            </div>
          </div>

          {error && <p className="error-msg" style={{ marginBottom: 12 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create Invoice'}
            </button>
            <button type="button" className="btn btn-outline" onClick={() => router.back()}>Cancel</button>
          </div>
        </form>
      </main>
    </div>
  );
}
