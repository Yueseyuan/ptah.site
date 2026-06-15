'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listTradelines } from '@/lib/api';

interface Tradeline { id: number; bureau: string; creditor_name: string; account_number_last4: string; account_type: string; open_date: string; balance: number | null; credit_limit: number | null; payment_status: string; derogatory: boolean; dispute_status: string; }

const BUREAUS = ['experian', 'equifax', 'transunion', 'innovis'];

export default function TradelinesPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [tradelines, setTradelines] = useState<Tradeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [bureauFilter, setBureauFilter] = useState('');

  useEffect(() => {
    listTradelines(caseId, bureauFilter || undefined).then(setTradelines).finally(() => setLoading(false));
  }, [caseId, bureauFilter]);

  const grouped: Record<string, Tradeline[]> = {};
  tradelines.forEach(t => { if (!grouped[t.bureau]) grouped[t.bureau] = []; grouped[t.bureau].push(t); });

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header"><h1>Tradelines</h1><p>{tradelines.length} accounts across all bureaus</p></div>
        <CaseNav caseId={caseId} />

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button onClick={() => setBureauFilter('')} className={!bureauFilter ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>All</button>
          {BUREAUS.map(b => (
            <button key={b} onClick={() => setBureauFilter(b)} className={bureauFilter === b ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
              {b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
        </div>

        {loading ? <div className="spinner" /> : tradelines.length === 0 ? (
          <div className="card"><p className="empty">No tradelines found. Upload credit reports to parse tradelines.</p></div>
        ) : (
          Object.entries(grouped).map(([bureau, tls]) => (
            <div className="card" key={bureau} style={{ marginBottom: 16 }}>
              <h3 style={{ textTransform: 'capitalize', marginBottom: 12 }}>{bureau} ({tls.length} accounts)</h3>
              <table>
                <thead><tr><th>Creditor</th><th>Account</th><th>Type</th><th>Status</th><th>Balance</th><th>Limit</th><th>Open Date</th><th>Dispute</th></tr></thead>
                <tbody>
                  {tls.map(t => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: t.derogatory ? 600 : 400, color: t.derogatory ? 'var(--danger)' : 'inherit' }}>
                        {t.derogatory && '⚠ '}{t.creditor_name}
                      </td>
                      <td><code>xxxx-{t.account_number_last4}</code></td>
                      <td>{t.account_type}</td>
                      <td><span className={`badge badge-${t.payment_status === 'current' ? 'success' : t.derogatory ? 'high' : 'pending'}`}>{t.payment_status}</span></td>
                      <td>{t.balance != null ? `$${t.balance.toLocaleString()}` : '—'}</td>
                      <td>{t.credit_limit != null ? `$${t.credit_limit.toLocaleString()}` : '—'}</td>
                      <td style={{ fontSize: 12, color: 'var(--muted)' }}>{t.open_date || '—'}</td>
                      <td><span className={`badge badge-${t.dispute_status === 'none' ? 'pending' : t.dispute_status === 'resolved' ? 'success' : 'medium'}`}>{t.dispute_status}</span></td>
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
