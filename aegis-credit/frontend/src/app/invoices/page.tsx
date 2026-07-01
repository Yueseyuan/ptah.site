'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listInvoices, listClients, createInvoice, markInvoicePaid, getInvoicePdf } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Client { id: number; first_name: string; last_name: string; }

interface LineItem {
  description: string;
  qty: string;
  price: string;
}

interface Invoice {
  id: number;
  invoice_number: string;
  client_id: number;
  client_name?: string;
  division: string;
  total: number;
  status: string;
  due_date: string;
  notes: string;
  line_items: LineItem[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DIVISIONS = ['Credit Repair', 'Debt Settlement', 'Legal', 'Consulting', 'Collections', 'Other'];
const FILTER_TABS = ['All', 'Draft', 'Sent', 'Paid', 'Void'] as const;
type FilterTab = typeof FILTER_TABS[number];

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  draft: { bg: '#f3f4f6', color: '#374151' },
  sent:  { bg: '#dbeafe', color: '#1e40af' },
  paid:  { bg: '#d1fae5', color: '#065f46' },
  void:  { bg: '#fee2e2', color: '#991b1b' },
};

const EMPTY_LINE: LineItem = { description: '', qty: '1', price: '' };

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n ?? 0);
}

function fmtDate(d: string) {
  if (!d) return '—';
  try { return new Date(d).toLocaleDateString(); } catch { return d; }
}

function lineTotal(item: LineItem) {
  const q = parseFloat(item.qty) || 0;
  const p = parseFloat(item.price) || 0;
  return q * p;
}

function calcSubtotal(items: LineItem[]) {
  return items.reduce((s, i) => s + lineTotal(i), 0);
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status?.toLowerCase()] || { bg: '#f3f4f6', color: '#374151' };
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 4,
      padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
    }}>
      {status}
    </span>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: 'white', borderRadius: 'var(--radius)', width: 700, maxWidth: '96vw', maxHeight: '92vh', overflowY: 'auto', padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--navy)' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--muted)', lineHeight: 1 }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [clientMap, setClientMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<FilterTab>('All');
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [clientSearch, setClientSearch] = useState('');
  const [selectedClientId, setSelectedClientId] = useState('');
  const [division, setDivision] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [lineItems, setLineItems] = useState<LineItem[]>([{ ...EMPTY_LINE }]);

  function fetchAll() {
    setLoading(true);
    Promise.all([listInvoices(), listClients()])
      .then(([inv, cls]) => {
        setInvoices(inv);
        const m: Record<number, string> = {};
        for (const c of cls) m[c.id] = `${c.first_name} ${c.last_name}`;
        setClientMap(m);
        setClients(cls);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => { fetchAll(); }, []);

  // Totals
  const totalBilled = invoices.reduce((s, i) => s + (i.total || 0), 0);
  const totalPaid = invoices.filter(i => i.status?.toLowerCase() === 'paid').reduce((s, i) => s + (i.total || 0), 0);
  const outstanding = totalBilled - totalPaid;

  // Filtered
  const visible = tab === 'All'
    ? invoices
    : invoices.filter(i => i.status?.toLowerCase() === tab.toLowerCase());

  // Client search in modal
  const filteredClients = clientSearch.trim()
    ? clients.filter(c => `${c.first_name} ${c.last_name}`.toLowerCase().includes(clientSearch.toLowerCase())).slice(0, 8)
    : clients.slice(0, 8);

  function openModal() {
    setClientSearch('');
    setSelectedClientId('');
    setDivision('');
    setDueDate('');
    setNotes('');
    setLineItems([{ ...EMPTY_LINE }]);
    setFormError('');
    setShowModal(true);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedClientId) { setFormError('Please select a client.'); return; }
    const items = lineItems.filter(l => l.description.trim());
    if (items.length === 0) { setFormError('Add at least one line item.'); return; }
    setSaving(true);
    setFormError('');
    try {
      await createInvoice({
        client_id: parseInt(selectedClientId),
        division,
        due_date: dueDate || null,
        notes,
        line_items: items.map(l => ({
          description: l.description,
          qty: parseFloat(l.qty) || 1,
          price: parseFloat(l.price) || 0,
        })),
        total: calcSubtotal(items),
      });
      setSuccess('Invoice created successfully.');
      setShowModal(false);
      fetchAll();
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setFormError(e.response?.data?.detail || 'Failed to create invoice.');
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkPaid(id: number) {
    if (!confirm('Mark this invoice as paid?')) return;
    try {
      await markInvoicePaid(id);
      setInvoices(prev => prev.map(i => i.id === id ? { ...i, status: 'paid' } : i));
      setSuccess('Invoice marked as paid.');
      setTimeout(() => setSuccess(''), 3000);
    } catch {
      alert('Failed to mark invoice as paid.');
    }
  }

  async function handleViewPdf(id: number) {
    try {
      const blob = await getInvoicePdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch {
      alert('PDF not available for this invoice.');
    }
  }

  function updateLine(idx: number, field: keyof LineItem, value: string) {
    setLineItems(prev => prev.map((l, i) => i === idx ? { ...l, [field]: value } : l));
  }

  function addLine() {
    setLineItems(prev => [...prev, { ...EMPTY_LINE }]);
  }

  function removeLine(idx: number) {
    setLineItems(prev => prev.filter((_, i) => i !== idx));
  }

  const subtotal = calcSubtotal(lineItems);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">

        {/* Header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Invoices</h1>
            <p>{invoices.length} invoice{invoices.length !== 1 ? 's' : ''} total</p>
          </div>
          <button className="btn btn-primary" onClick={openModal}>+ New Invoice</button>
        </div>

        {success && <div className="alert alert-success">{success}</div>}

        {/* Summary totals */}
        <div className="stat-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Total Billed', value: fmt(totalBilled) },
            { label: 'Total Paid', value: fmt(totalPaid) },
            { label: 'Outstanding', value: fmt(outstanding) },
          ].map(({ label, value }) => (
            <div key={label} className="stat-card">
              <div className="label">{label}</div>
              <div className="value" style={{ fontSize: 20 }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
          {FILTER_TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '8px 14px', fontSize: 13, fontWeight: 500,
                color: tab === t ? 'var(--navy)' : 'var(--muted)',
                borderBottom: tab === t ? '2px solid var(--navy)' : '2px solid transparent',
                marginBottom: -1,
              }}>
              {t}
              <span style={{ marginLeft: 6, fontSize: 11, background: tab === t ? 'var(--navy)' : 'var(--border)', color: tab === t ? 'white' : 'var(--muted)', borderRadius: 10, padding: '0 6px' }}>
                {t === 'All' ? invoices.length : invoices.filter(i => i.status?.toLowerCase() === t.toLowerCase()).length}
              </span>
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="spinner" />
          ) : visible.length === 0 ? (
            <p className="empty">No invoices found{tab !== 'All' ? ` with status "${tab}"` : ''}.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Client</th>
                  <th>Division</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Due Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.map(inv => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: 600 }}>
                      <code>{inv.invoice_number || `INV-${inv.id}`}</code>
                    </td>
                    <td>{inv.client_name || clientMap[inv.client_id] || `Client #${inv.client_id}`}</td>
                    <td style={{ color: 'var(--muted)' }}>{inv.division || '—'}</td>
                    <td style={{ fontWeight: 600 }}>{fmt(inv.total)}</td>
                    <td><StatusBadge status={inv.status} /></td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>{fmtDate(inv.due_date)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-outline btn-sm" onClick={() => handleViewPdf(inv.id)}>
                          View PDF
                        </button>
                        {inv.status?.toLowerCase() !== 'paid' && inv.status?.toLowerCase() !== 'void' && (
                          <button
                            onClick={() => handleMarkPaid(inv.id)}
                            style={{ padding: '4px 10px', fontSize: 12, background: '#d1fae5', color: '#065f46', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 500 }}>
                            Mark Paid
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Create Invoice Modal */}
        {showModal && (
          <Modal title="New Invoice" onClose={() => setShowModal(false)}>
            {formError && <div className="alert alert-error">{formError}</div>}
            <form onSubmit={handleCreate}>

              {/* Client search */}
              <div className="form-group">
                <label>Client *</label>
                <input
                  type="text"
                  placeholder="Search client by name…"
                  value={clientSearch}
                  autoComplete="off"
                  onChange={e => { setClientSearch(e.target.value); setSelectedClientId(''); }}
                />
                {clientSearch && !selectedClientId && (
                  <div style={{ border: '1px solid var(--border)', borderRadius: 6, marginTop: 4, background: 'white', maxHeight: 180, overflowY: 'auto', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                    {filteredClients.length === 0 ? (
                      <div style={{ padding: '8px 12px', color: 'var(--muted)', fontSize: 13 }}>No clients found.</div>
                    ) : filteredClients.map(c => (
                      <div key={c.id}
                        onClick={() => { setSelectedClientId(String(c.id)); setClientSearch(`${c.first_name} ${c.last_name}`); }}
                        style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 13, borderBottom: '1px solid var(--border)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = '#f5f6fa')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'white')}>
                        {c.first_name} {c.last_name}
                      </div>
                    ))}
                  </div>
                )}
                {selectedClientId && (
                  <div style={{ fontSize: 12, color: 'var(--success)', marginTop: 4 }}>
                    Client selected (ID: {selectedClientId})
                  </div>
                )}
              </div>

              <div className="grid-2">
                <div className="form-group">
                  <label>Division</label>
                  <select value={division} onChange={e => setDivision(e.target.value)}>
                    <option value="">— Select division —</option>
                    {DIVISIONS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Due Date</label>
                  <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
                </div>
              </div>

              {/* Line items */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <label style={{ fontSize: 12, fontWeight: 500 }}>Line Items *</label>
                  <button type="button" className="btn btn-outline btn-sm" onClick={addLine}>+ Add Line</button>
                </div>

                {/* Header row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 100px 80px 28px', gap: 6, marginBottom: 4 }}>
                  {['Description', 'Qty', 'Unit Price', 'Subtotal', ''].map(h => (
                    <div key={h} style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0 2px' }}>
                      {h}
                    </div>
                  ))}
                </div>

                {lineItems.map((item, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr 80px 100px 80px 28px', gap: 6, marginBottom: 6, alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="Service description…"
                      value={item.description}
                      onChange={e => updateLine(idx, 'description', e.target.value)}
                      style={{ padding: '6px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 13 }}
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.qty}
                      onChange={e => updateLine(idx, 'qty', e.target.value)}
                      style={{ padding: '6px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 13, textAlign: 'right' }}
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={item.price}
                      onChange={e => updateLine(idx, 'price', e.target.value)}
                      style={{ padding: '6px 8px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 13, textAlign: 'right' }}
                    />
                    <div style={{ fontSize: 13, fontWeight: 600, textAlign: 'right', color: 'var(--navy)', padding: '0 4px' }}>
                      {fmt(lineTotal(item))}
                    </div>
                    {lineItems.length > 1 ? (
                      <button
                        type="button"
                        onClick={() => removeLine(idx)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 18, lineHeight: 1, padding: 0 }}
                        title="Remove line">
                        ×
                      </button>
                    ) : <div />}
                  </div>
                ))}

                {/* Totals */}
                <div style={{ borderTop: '2px solid var(--border)', marginTop: 8, paddingTop: 10, display: 'flex', justifyContent: 'flex-end', gap: 16 }}>
                  <div style={{ fontSize: 13, color: 'var(--muted)' }}>Subtotal</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)', minWidth: 80, textAlign: 'right' }}>{fmt(subtotal)}</div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)' }}>Total</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--navy)', minWidth: 80, textAlign: 'right' }}>{fmt(subtotal)}</div>
                </div>
              </div>

              <div className="form-group">
                <label>Notes</label>
                <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Payment terms, additional information…" />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Creating…' : 'Create Invoice'}
                </button>
              </div>
            </form>
          </Modal>
        )}

      </main>
    </div>
  );
}
