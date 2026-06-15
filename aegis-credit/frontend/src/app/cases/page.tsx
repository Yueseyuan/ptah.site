'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listCases } from '@/lib/api';

interface Case { id: number; case_number: string; client_id: number; status: string; goal: string; created_at: string; }

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6', active: '#10b981', on_hold: '#f59e0b', closed: '#6b7280',
};

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    listCases().then(setCases).finally(() => setLoading(false));
  }, []);

  const visible = filter ? cases.filter(c => c.status === filter) : cases;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Cases</h1><p>All credit investigation cases</p></div>
          <Link href="/cases/new" className="btn btn-primary">+ New Case</Link>
        </div>

        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
          {['', 'intake', 'active', 'on_hold', 'closed'].map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={filter === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
              {s || 'All'}
            </button>
          ))}
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : visible.length === 0 ? (
            <p className="empty">No cases found. <Link href="/cases/new">Create one.</Link></p>
          ) : (
            <table>
              <thead><tr><th>Case #</th><th>Client</th><th>Status</th><th>Goal</th><th>Opened</th><th></th></tr></thead>
              <tbody>
                {visible.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}><Link href={`/cases/${c.id}`}><code>{c.case_number}</code></Link></td>
                    <td><Link href={`/clients/${c.client_id}`}>Client #{c.client_id}</Link></td>
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
