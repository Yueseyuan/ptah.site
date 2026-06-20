'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listCases } from '@/lib/api';

const DIVISION_LABELS: Record<string, string> = {
  notary: 'Notary', credit: 'Credit', reentry: 'Reentry',
  document_prep: 'Doc Prep', asset_recovery: 'Asset Recovery', business_formation: 'Business',
};
const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6', in_progress: '#f59e0b', completed: '#10b981', closed: '#6b7280',
};

interface Case {
  id: number; division: string; status: string;
  client_id: number; created_at: string;
}

export default function CasesPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setCases(await listCases()); } finally { setLoading(false); }
  }

  const visible = filter ? cases.filter((c) => c.division === filter || c.status === filter) : cases;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Cases</h1><p>All active and archived cases</p></div>
          <Link href="/cases/new" className="btn btn-primary">+ New Case</Link>
        </div>

        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {['', 'intake', 'in_progress', 'completed', 'closed'].map((s) => (
            <button key={s} onClick={() => setFilter(s)}
              className={filter === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
              {s || 'All'}
            </button>
          ))}
          <span style={{ flex: 1 }} />
          {Object.entries(DIVISION_LABELS).map(([k, v]) => (
            <button key={k} onClick={() => setFilter(filter === k ? '' : k)}
              className={filter === k ? 'btn btn-gold btn-sm' : 'btn btn-outline btn-sm'}>
              {v}
            </button>
          ))}
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : visible.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
              No cases found. <Link href="/cases/new">Open the first one.</Link>
            </p>
          ) : (
            <table>
              <thead>
                <tr><th>Case</th><th>Client</th><th>Division</th><th>Status</th><th>Date</th><th></th></tr>
              </thead>
              <tbody>
                {visible.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}><Link href={`/cases/${c.id}`}>Case #{c.id} — {DIVISION_LABELS[c.division] || c.division}</Link></td>
                    <td><Link href={`/clients/${c.client_id}`}>Client #{c.client_id}</Link></td>
                    <td>{DIVISION_LABELS[c.division] || c.division}</td>
                    <td>
                      <span style={{
                        background: STATUS_COLORS[c.status] || '#999', color: 'white',
                        borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
                      }}>{c.status.replace('_', ' ')}</span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: 13 }}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
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
