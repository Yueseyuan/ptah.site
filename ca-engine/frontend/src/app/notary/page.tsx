'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';

const ACT_TYPES = ['acknowledgment', 'jurat', 'oath', 'affirmation', 'copy_certification', 'signature_witnessing', 'other'];
const FEE_CAP = 5.00;

export default function NotaryPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ client_id: '', act_type: 'acknowledgment', fee: '5.00', notes: '', performed_at: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { const { data } = await api.get('/api/notary'); setLogs(data); } finally { setLoading(false); }
  }

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const fee = parseFloat(form.fee);
    if (fee > FEE_CAP) { setError(`SC Code §26-1-120: fee may not exceed $${FEE_CAP.toFixed(2)} per notarial act.`); return; }
    setSaving(true);
    try {
      await api.post('/api/notary', {
        ...form,
        client_id: Number(form.client_id),
        fee,
        performed_at: form.performed_at || new Date().toISOString(),
      });
      setShowForm(false);
      setForm({ client_id: '', act_type: 'acknowledgment', fee: '5.00', notes: '', performed_at: '' });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save notary log.');
    } finally { setSaving(false); }
  }

  const totalFees = logs.reduce((s, l) => s + (l.fee || 0), 0);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Notary Log</h1>
            <p>SC Code §26-1-120 — fee cap $5.00 per notarial act</p>
          </div>
          <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
            {showForm ? 'Cancel' : '+ Log Notarial Act'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16, fontSize: 15 }}>New Notarial Act</h3>
            <form onSubmit={handleSubmit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Client ID *</label>
                  <input type="number" value={form.client_id} onChange={(e) => set('client_id', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Act Type *</label>
                  <select value={form.act_type} onChange={(e) => set('act_type', e.target.value)}>
                    {ACT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label>Fee (max ${FEE_CAP.toFixed(2)}) *</label>
                  <input type="number" step="0.01" min="0" max={FEE_CAP}
                    value={form.fee} onChange={(e) => set('fee', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Date Performed</label>
                  <input type="datetime-local" value={form.performed_at} onChange={(e) => set('performed_at', e.target.value)} />
                </div>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
              </div>
              {error && <p className="error-msg" style={{ marginBottom: 8 }}>{error}</p>}
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Log Act'}
              </button>
            </form>
          </div>
        )}

        <div className="stat-grid" style={{ marginBottom: 16 }}>
          <div className="stat-card">
            <div className="label">Total Acts</div>
            <div className="value">{logs.length}</div>
          </div>
          <div className="stat-card">
            <div className="label">Total Fees Collected</div>
            <div className="value">${totalFees.toFixed(2)}</div>
          </div>
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : logs.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>No notarial acts logged yet.</p>
          ) : (
            <table>
              <thead><tr><th>Client</th><th>Act Type</th><th>Fee</th><th>Date</th><th>Notes</th></tr></thead>
              <tbody>
                {logs.map((l: any) => (
                  <tr key={l.id}>
                    <td>#{l.client_id}</td>
                    <td>{l.act_type?.replace(/_/g, ' ')}</td>
                    <td>${(l.fee || 0).toFixed(2)}</td>
                    <td style={{ fontSize: 13, color: 'var(--muted)' }}>{new Date(l.performed_at).toLocaleString()}</td>
                    <td style={{ fontSize: 13, color: 'var(--muted)' }}>{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 12 }}>
          SC Code §26-1-120: Maximum fee of $5.00 per notarial act. All fees are enforced at API level.
        </p>
      </main>
    </div>
  );
}
