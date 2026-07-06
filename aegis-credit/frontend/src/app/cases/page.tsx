'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listCases, listClients } from '@/lib/api';

interface Case { id: number; case_number: string; client_id: number; status: string; goal: string; created_at: string; }
interface Client { id: number; first_name: string; last_name: string; }

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6', active: '#10b981', on_hold: '#f59e0b', closed: '#6b7280',
};

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [clientMap, setClientMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    Promise.all([listCases(), listClients()]).then(([cs, cls]) => {
      setCases(cs);
      const m: Record<number, string> = {};
      for (const c of cls) m[c.id] = `${c.first_name} ${c.last_name}`;
      setClientMap(m);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const q = search.toLowerCase().trim();
  const visible = cases.filter(c => {
    if (statusFilter && c.status !== statusFilter) return false;
    if (!q) return true;
    const clientName = (clientMap[c.client_id] || '').toLowerCase();
    return (
      c.case_number.toLowerCase().includes(q) ||
      clientName.includes(q) ||
      (c.goal || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Cases</h1>
            <p>{visible.length} of {cases.length} case{cases.length !== 1 ? 's' : ''}</p>
          </div>
          <Link href="/cases/new" className="btn btn-primary">+ New Case</Link>
        </div>

        <div className="card" style={{ marginBottom: 12 }}>
          <input
            type="text"
            placeholder="Search by case #, client name, or goal…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13, marginBottom: 10 }}
          />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {['', 'intake', 'active', 'on_hold', 'closed'].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={statusFilter === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
                {s ? s.replace('_', ' ') : 'All'}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : visible.length === 0 ? (
            <p className="empty">
              {cases.length === 0
                ? <><span>No cases found. </span><Link href="/cases/new">Create one.</Link></>
                : 'No cases match your filters.'}
            </p>
          ) : (
            <table>
              <thead><tr><th>Case #</th><th>Client</th><th>Status</th><th>Goal</th><th>Opened</th><th></th></tr></thead>
              <tbody>
                {visible.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}><Link href={`/cases/${c.id}`}><code>{c.case_number}</code></Link></td>
                    <td>
                      <Link href={`/clients/${c.client_id}`}>
                        {clientMap[c.client_id] || `Client #${c.client_id}`}
                      </Link>
                    </td>
                    <td>
                      <span style={{ background: STATUS_COLORS[c.status] || '#999', color: 'white', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600 }}>
                        {c.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.goal || '—'}</td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td><Link href={`/cases/${c.id}`} className="btn btn-outline btn-sm">View</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
