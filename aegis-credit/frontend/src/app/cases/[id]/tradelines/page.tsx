'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listTradelines, updateTradeline } from '@/lib/api';
import axios from 'axios';

interface Tradeline { id: number; bureau: string; creditor_name: string; account_number_last4: string; account_type: string; open_date: string; balance: number | null; credit_limit: number | null; payment_status: string; derogatory: boolean; dispute_status: string; }

const BUREAUS = ['experian', 'equifax', 'transunion', 'innovis'];
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

const blankForm = {
  bureau: 'experian', creditor_name: '', account_number_last4: '', account_type: 'credit_card',
  open_date: '', balance: '', credit_limit: '', payment_status: 'current', derogatory: false,
};

export default function TradelinesPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [tradelines, setTradelines] = useState<Tradeline[]>([]);
  const [reports, setReports] = useState<{ id: number; bureau: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [bureauFilter, setBureauFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...blankForm });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function load() {
    listTradelines(caseId, bureauFilter || undefined).then(setTradelines).finally(() => setLoading(false));
    axios.get(`${API}/api/reports/case/${caseId}`).then(r => setReports(r.data)).catch(() => {});
  }
  useEffect(() => { load(); }, [caseId, bureauFilter]);

  async function addTradeline(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError('');
    try {
      const reportForBureau = reports.find(r => r.bureau === form.bureau || r.bureau === 'all');
      if (!reportForBureau) {
        setError(`No uploaded report found for ${form.bureau}. Upload a report for this bureau first, then add tradelines.`);
        setSaving(false); return;
      }
      await axios.post(`${API}/api/tradelines/manual`, {
        case_id: caseId,
        report_id: reportForBureau.id,
        bureau: form.bureau,
        creditor_name: form.creditor_name,
        account_number_last4: form.account_number_last4,
        account_type: form.account_type,
        open_date: form.open_date,
        balance: form.balance ? parseFloat(form.balance) : null,
        credit_limit: form.credit_limit ? parseFloat(form.credit_limit) : null,
        payment_status: form.payment_status,
        derogatory: form.derogatory,
      });
      setForm({ ...blankForm });
      setShowForm(false);
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Failed to add tradeline.');
    } finally { setSaving(false); }
  }

  const grouped: Record<string, Tradeline[]> = {};
  tradelines.forEach(t => { if (!grouped[t.bureau]) grouped[t.bureau] = []; grouped[t.bureau].push(t); });

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Tradelines</h1><p>{tradelines.length} accounts across all bureaus</p></div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Manually'}</button>
        </div>
        <CaseNav caseId={caseId} />

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add Tradeline Manually</h3>
            <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 12 }}>
              You must have already uploaded a report for the selected bureau. The tradeline will be linked to that report.
            </p>
            {error && <div className="alert-error">{error}</div>}
            <form onSubmit={addTradeline}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Bureau *</label>
                  <select value={form.bureau} onChange={e => setForm(f => ({ ...f, bureau: e.target.value }))}>
                    {BUREAUS.map(b => <option key={b} value={b}>{b.charAt(0).toUpperCase() + b.slice(1)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Creditor Name *</label>
                  <input required value={form.creditor_name} onChange={e => setForm(f => ({ ...f, creditor_name: e.target.value }))} placeholder="e.g., Capital One, Chase" />
                </div>
                <div className="form-group">
                  <label>Account Last 4</label>
                  <input maxLength={4} value={form.account_number_last4} onChange={e => setForm(f => ({ ...f, account_number_last4: e.target.value.replace(/\D/g, '').slice(0, 4) }))} placeholder="1234" />
                </div>
                <div className="form-group">
                  <label>Account Type</label>
                  <select value={form.account_type} onChange={e => setForm(f => ({ ...f, account_type: e.target.value }))}>
                    <option value="credit_card">Credit Card</option>
                    <option value="auto_loan">Auto Loan</option>
                    <option value="mortgage">Mortgage</option>
                    <option value="student_loan">Student Loan</option>
                    <option value="collection">Collection</option>
                    <option value="personal_loan">Personal Loan</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Payment Status</label>
                  <select value={form.payment_status} onChange={e => setForm(f => ({ ...f, payment_status: e.target.value }))}>
                    <option value="current">Current</option>
                    <option value="30_days_late">30 Days Late</option>
                    <option value="60_days_late">60 Days Late</option>
                    <option value="90_days_late">90 Days Late</option>
                    <option value="charge_off">Charge-Off</option>
                    <option value="collection">Collection</option>
                    <option value="paid">Paid</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Open Date</label>
                  <input type="date" value={form.open_date} onChange={e => setForm(f => ({ ...f, open_date: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Balance ($)</label>
                  <input type="number" value={form.balance} onChange={e => setForm(f => ({ ...f, balance: e.target.value }))} placeholder="0.00" />
                </div>
                <div className="form-group">
                  <label>Credit Limit ($)</label>
                  <input type="number" value={form.credit_limit} onChange={e => setForm(f => ({ ...f, credit_limit: e.target.value }))} placeholder="0.00" />
                </div>
              </div>
              <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14, fontWeight: 400 }}>
                <input type="checkbox" checked={form.derogatory} onChange={e => setForm(f => ({ ...f, derogatory: e.target.checked }))} style={{ width: 'auto' }} />
                Derogatory item
              </label>
              <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Add Tradeline'}</button>
            </form>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button onClick={() => setBureauFilter('')} className={!bureauFilter ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>All</button>
          {BUREAUS.map(b => (
            <button key={b} onClick={() => setBureauFilter(b)} className={bureauFilter === b ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
              {b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
        </div>

        {loading ? <div className="spinner" /> : tradelines.length === 0 ? (
          <div className="card">
            <p className="empty" style={{ marginBottom: 12 }}>No tradelines found.</p>
            <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted)' }}>
              Either set <code>ANTHROPIC_API_KEY</code> in the backend <code>.env</code> file and reparse your reports,
              or click <b>+ Add Manually</b> above to enter tradelines by hand.
            </p>
          </div>
        ) : (
          Object.entries(grouped).map(([bureau, tls]) => (
            <div className="card" key={bureau} style={{ marginBottom: 16 }}>
              <h3 style={{ textTransform: 'capitalize', marginBottom: 12 }}>{bureau} ({tls.length} accounts)</h3>
              <table>
                <thead>
                  <tr><th>Creditor</th><th>Account</th><th>Type</th><th>Status</th><th>Balance</th><th>Limit</th><th>Open Date</th><th>Dispute</th></tr>
                </thead>
                <tbody>
                  {tls.map(t => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: t.derogatory ? 600 : 400, color: t.derogatory ? 'var(--danger)' : 'inherit' }}>
                        {t.derogatory && '⚠ '}{t.creditor_name}
                      </td>
                      <td><code>xxxx-{t.account_number_last4 || '????'}</code></td>
                      <td>{t.account_type}</td>
                      <td>
                        <span className={`badge badge-${t.payment_status === 'current' ? 'success' : t.derogatory ? 'high' : 'pending'}`}>
                          {t.payment_status}
                        </span>
                      </td>
                      <td>{t.balance != null ? `$${t.balance.toLocaleString()}` : '—'}</td>
                      <td>{t.credit_limit != null ? `$${t.credit_limit.toLocaleString()}` : '—'}</td>
                      <td style={{ fontSize: 12, color: 'var(--muted)' }}>{t.open_date || '—'}</td>
                      <td>
                        <span className={`badge badge-${t.dispute_status === 'none' ? 'pending' : t.dispute_status === 'resolved' ? 'success' : 'medium'}`}>
                          {t.dispute_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
