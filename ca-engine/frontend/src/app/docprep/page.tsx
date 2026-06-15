'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listDocPrepOrders, createDocPrepOrder, listClients } from '@/lib/api';

interface DocPrepOrder {
  id: number;
  order_number: string;
  client_id: number;
  status: string;
  doc_category: string;
  total_fee: number;
  notes: string;
  created_at: string;
}

interface Client { id: number; first_name: string; last_name: string; }

const CATEGORIES = ['general', 'hkp', 'business', 'estate', 'real_estate', 'dispute'];

const DOC_TYPES: Record<string, string[]> = {
  hkp: ['Letter of Credit (LOC)', 'Promissory Note', 'Membership Certificate', 'Operating Agreement', 'Profit Sharing Agreement'],
  business: ['Business Plan', 'SOP', 'Operating Agreement', 'LLC Checklist'],
  estate: ['Affidavit of Heirship', 'Estate Summary Letter'],
  real_estate: ['Purchase Agreement', 'Lease Agreement', 'Title Package'],
  dispute: ['Debt Validation Letter', 'Cease & Desist', 'FCRA Dispute'],
  general: ['Cover Letter', 'Notarized Statement', 'Power of Attorney'],
};

const blank = { client_id: '', doc_category: 'general', notes: '' };

export default function DocPrepPage() {
  const [orders, setOrders] = useState<DocPrepOrder[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [o, c] = await Promise.all([listDocPrepOrders(), listClients()]);
      setOrders(o);
      setClients(c);
    } catch { /* backend offline */ }
  }

  useEffect(() => { load(); }, []);

  function toggleType(t: string) {
    setSelectedTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload: Record<string, unknown> = {
        client_id: Number(form.client_id),
        doc_category: form.doc_category,
        doc_types: selectedTypes,
      };
      if (form.notes) payload.notes = form.notes;
      await createDocPrepOrder(payload);
      setForm(blank);
      setSelectedTypes([]);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      setErr(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message || 'Failed to create order.');
    } finally {
      setSaving(false);
    }
  }

  const clientName = (id: number) => {
    const c = clients.find(c => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : `#${id}`;
  };

  const availableTypes = DOC_TYPES[form.doc_category] || DOC_TYPES.general;
  const estimatedFee = Math.max(50, selectedTypes.length * 35);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Division 4 — Document Prep</h1>
            <p>HKP instruments, business docs, estate, real estate &amp; dispute packages.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Cancel' : '+ New Order'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Create Document Order</h3>
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
                  <label>Document Category *</label>
                  <select value={form.doc_category}
                    onChange={e => { setForm(f => ({ ...f, doc_category: e.target.value })); setSelectedTypes([]); }}>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c.toUpperCase()}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Document Types</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 6 }}>
                    {availableTypes.map(t => (
                      <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontWeight: 400, color: 'var(--text)' }}>
                        <input type="checkbox" checked={selectedTypes.includes(t)} onChange={() => toggleType(t)} style={{ width: 'auto' }} />
                        {t}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Notes</label>
                  <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
                </div>
              </div>
              <p style={{ fontSize: 13, color: 'var(--muted)', margin: '8px 0 12px' }}>
                Estimated fee: <strong>${estimatedFee}</strong> ({selectedTypes.length} doc{selectedTypes.length !== 1 ? 's' : ''})
              </p>
              <button type="submit" className="btn btn-primary" disabled={saving || selectedTypes.length === 0}>
                {saving ? 'Creating…' : 'Create Order'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Order #</th>
                <th>Client</th>
                <th>Category</th>
                <th>Status</th>
                <th>Fee</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>No orders yet.</td></tr>
              )}
              {orders.map(o => (
                <tr key={o.id}>
                  <td><code>{o.order_number}</code></td>
                  <td>{clientName(o.client_id)}</td>
                  <td>{o.doc_category.toUpperCase()}</td>
                  <td><span className={`badge badge-${o.status}`}>{o.status}</span></td>
                  <td>${o.total_fee}</td>
                  <td>{new Date(o.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
