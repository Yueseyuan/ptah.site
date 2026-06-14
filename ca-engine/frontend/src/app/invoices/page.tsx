'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listInvoices, recordPayment, invoicePdfUrl } from '@/lib/api';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [payingId, setPayingId] = useState<number | null>(null);
  const [payAmount, setPayAmount] = useState('');
  const [payNotes, setPayNotes] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setInvoices(await listInvoices()); } finally { setLoading(false); }
  }

  async function submitPayment(e: React.FormEvent, id: number) {
    e.preventDefault();
    await recordPayment(id, parseFloat(payAmount), payNotes);
    setPayingId(null);
    setPayAmount('');
    setPayNotes('');
    await load();
  }

  const total = invoices.reduce((s, i) => s + (i.amount || 0), 0);
  const collected = invoices.reduce((s, i) => s + (i.amount_paid || 0), 0);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Invoices</h1><p>Billing and payment tracking</p></div>
          <Link href="/invoices/new" className="btn btn-primary">+ New Invoice</Link>
        </div>

        <div className="stat-grid" style={{ marginBottom: 16 }}>
          <div className="stat-card">
            <div className="label">Total Invoiced</div>
            <div className="value">${total.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="label">Collected</div>
            <div className="value">${collected.toLocaleString()}</div>
          </div>
          <div className="stat-card">
            <div className="label">Outstanding</div>
            <div className="value">${(total - collected).toLocaleString()}</div>
          </div>
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : invoices.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
              No invoices yet. <Link href="/invoices/new">Create the first one.</Link>
            </p>
          ) : (
            <>
              <table>
                <thead>
                  <tr><th>#</th><th>Client</th><th>Description</th><th>Amount</th><th>Paid</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {invoices.map((inv: any) => (
                    <>
                      <tr key={inv.id}>
                        <td style={{ color: 'var(--muted)', fontSize: 13 }}>#{inv.id}</td>
                        <td>#{inv.client_id}</td>
                        <td>{inv.description}</td>
                        <td>${(inv.amount || 0).toLocaleString()}</td>
                        <td>${(inv.amount_paid || 0).toLocaleString()}</td>
                        <td>
                          <span style={{
                            background: inv.status === 'paid' ? '#10b981' : inv.status === 'sent' ? '#3b82f6' : '#f59e0b',
                            color: 'white', borderRadius: 4, padding: '2px 8px', fontSize: 11,
                          }}>{inv.status}</span>
                        </td>
                        <td style={{ display: 'flex', gap: 6 }}>
                          <a href={invoicePdfUrl(inv.id)} target="_blank" className="btn btn-outline btn-sm">PDF</a>
                          {inv.status !== 'paid' && (
                            <button onClick={() => setPayingId(payingId === inv.id ? null : inv.id)}
                              className="btn btn-gold btn-sm">Record Payment</button>
                          )}
                        </td>
                      </tr>
                      {payingId === inv.id && (
                        <tr key={`pay-${inv.id}`}>
                          <td colSpan={7} style={{ background: '#f8fafc', padding: '12px 16px' }}>
                            <form onSubmit={(e) => submitPayment(e, inv.id)} style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label>Amount</label>
                                <input type="number" step="0.01" value={payAmount}
                                  onChange={(e) => setPayAmount(e.target.value)} required style={{ width: 120 }} />
                              </div>
                              <div className="form-group" style={{ margin: 0, flex: 1 }}>
                                <label>Notes</label>
                                <input value={payNotes} onChange={(e) => setPayNotes(e.target.value)} />
                              </div>
                              <button type="submit" className="btn btn-primary btn-sm">Save</button>
                            </form>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
