'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listCases, listClients, listPendingPortalCases } from '@/lib/api';

interface Case {
  id: number;
  case_number: string;
  client_id: number;
  status: string;
  goal: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  intake: 'var(--info)',
  active: 'var(--success)',
  on_hold: 'var(--warning)',
  closed: 'var(--muted)',
};

export default function DashboardPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [clientCount, setClientCount] = useState(0);
  const [pendingIntake, setPendingIntake] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listCases(), listClients(), listPendingPortalCases().catch(() => [])])
      .then(([c, cl, intake]) => {
        setCases(c);
        setClientCount(cl.length);
        setPendingIntake((intake as {portal_status: string}[]).filter(i => i.portal_status === 'pending').length);
      })
      .finally(() => setLoading(false));
  }, []);

  const byStatus = cases.reduce<Record<string, number>>((acc, c) => {
    acc[c.status] = (acc[c.status] || 0) + 1;
    return acc;
  }, {});

  const openCases = cases.filter(c => c.status !== 'closed').length;
  const activeCases = byStatus['active'] || 0;
  const intakeCases = byStatus['intake'] || 0;
  const onHoldCases = byStatus['on_hold'] || 0;
  const recent = [...cases].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Dashboard</h1>
            <p>Overview of all active investigation cases</p>
          </div>
          <Link href="/cases/new" className="btn btn-primary">+ New Case</Link>
        </div>

        <div className="disclosure-banner">
          All findings require human review. Aegis provides investigation support only — not legal advice.
        </div>

        {loading ? <div className="spinner" /> : (
          <>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="label">Open Cases</div>
                <div className="value" style={{ color: 'var(--navy)' }}>{openCases}</div>
              </div>
              <div className="stat-card">
                <div className="label">Active</div>
                <div className="value" style={{ color: 'var(--success)' }}>{activeCases}</div>
              </div>
              <div className="stat-card">
                <div className="label">Intake</div>
                <div className="value" style={{ color: 'var(--info)' }}>{intakeCases}</div>
              </div>
              <div className="stat-card">
                <div className="label">On Hold</div>
                <div className="value" style={{ color: 'var(--warning)' }}>{onHoldCases}</div>
              </div>
              <div className="stat-card">
                <div className="label">Total Clients</div>
                <div className="value">{clientCount}</div>
              </div>
              <div className="stat-card">
                <div className="label">Total Cases</div>
                <div className="value">{cases.length}</div>
              </div>
              {pendingIntake > 0 && (
                <Link href="/admin/portal" style={{ textDecoration: 'none' }}>
                  <div className="stat-card" style={{ borderColor: '#f59e0b', cursor: 'pointer' }}>
                    <div className="label" style={{ color: '#92400e' }}>Portal Intake</div>
                    <div className="value" style={{ color: '#d97706' }}>{pendingIntake}</div>
                    <div style={{ fontSize: 10, color: '#92400e', marginTop: 2 }}>pending review →</div>
                  </div>
                </Link>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div className="card">
                <h3>Case Status Distribution</h3>
                {Object.entries(byStatus).length === 0 ? (
                  <p className="empty" style={{ padding: '20px 0' }}>No cases yet</p>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    {Object.entries(byStatus).map(([status, count]) => (
                      <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                        <div style={{
                          width: `${Math.round((count / cases.length) * 100)}%`,
                          maxWidth: '100%',
                          minWidth: 4,
                          height: 24,
                          background: STATUS_COLORS[status] || 'var(--muted)',
                          borderRadius: 4,
                          transition: 'width 0.3s',
                        }} />
                        <span style={{ fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
                          {status.replace('_', ' ')} ({count})
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h3>Quick Actions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                  <Link href="/cases/new" className="btn btn-outline" style={{ justifyContent: 'flex-start' }}>
                    + Open New Investigation Case
                  </Link>
                  <Link href="/clients/new" className="btn btn-outline" style={{ justifyContent: 'flex-start' }}>
                    + Add New Client
                  </Link>
                  <Link href="/cases" className="btn btn-outline" style={{ justifyContent: 'flex-start' }}>
                    View All Cases
                  </Link>
                  <Link href="/learning" className="btn btn-outline" style={{ justifyContent: 'flex-start' }}>
                    Learning Vault
                  </Link>
                </div>
              </div>
            </div>

            <div className="card">
              <h3>Recent Cases</h3>
              {recent.length === 0 ? (
                <p className="empty">No cases yet. <Link href="/cases/new">Create the first case.</Link></p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Case #</th>
                      <th>Status</th>
                      <th>Goal</th>
                      <th>Opened</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map(c => (
                      <tr key={c.id}>
                        <td style={{ fontWeight: 600 }}>
                          <Link href={`/cases/${c.id}`}><code>{c.case_number}</code></Link>
                        </td>
                        <td>
                          <span style={{
                            background: STATUS_COLORS[c.status] || 'var(--muted)',
                            color: 'white', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
                          }}>
                            {c.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td style={{ color: 'var(--muted)', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.goal || '—'}
                        </td>
                        <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                          {new Date(c.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          <Link href={`/cases/${c.id}`} className="btn btn-outline btn-sm">View</Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
