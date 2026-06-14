'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getDashboardStats, getAuditLog } from '@/lib/api';

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboardStats(), getAuditLog({ limit: 50 })])
      .then(([s, a]) => { setStats(s); setAudit(a); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Admin</h1>
          <p>System overview, audit log, and configuration</p>
        </div>

        {loading ? <div className="spinner" /> : (
          <>
            <div className="stat-grid" style={{ marginBottom: 16 }}>
              <div className="stat-card">
                <div className="label">Total Clients</div>
                <div className="value">{stats?.total_clients ?? 0}</div>
              </div>
              <div className="stat-card">
                <div className="label">Active Cases</div>
                <div className="value">{stats?.active_cases ?? 0}</div>
              </div>
              <div className="stat-card">
                <div className="label">Total Invoiced</div>
                <div className="value">${(stats?.invoiced_total ?? 0).toLocaleString()}</div>
              </div>
              <div className="stat-card">
                <div className="label">Collected</div>
                <div className="value">${(stats?.collected_total ?? 0).toLocaleString()}</div>
              </div>
            </div>

            <div className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ color: 'var(--navy)', marginBottom: 8, fontSize: 15 }}>Legal Disclosure</h3>
              <div className="disclosure-banner" style={{ margin: 0 }}>
                Cruel & Associates is not a law firm and does not provide legal advice or legal representation.
                We are not attorneys. Any legal services are provided exclusively by licensed attorneys.
                No legal pleadings are generated without attorney review. Administrative assistance only.
              </div>
            </div>

            <div className="card">
              <h3 style={{ color: 'var(--navy)', marginBottom: 16, fontSize: 15 }}>Audit Log (last 50)</h3>
              {audit.length === 0 ? (
                <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 24 }}>No audit entries.</p>
              ) : (
                <table>
                  <thead><tr><th>Action</th><th>Resource</th><th>User</th><th>Time</th></tr></thead>
                  <tbody>
                    {audit.map((a: any) => (
                      <tr key={a.id}>
                        <td style={{ fontWeight: 600 }}>{a.action}</td>
                        <td>{a.resource_type}{a.resource_id ? ` #${a.resource_id}` : ''}</td>
                        <td style={{ fontSize: 13, color: 'var(--muted)' }}>User #{a.user_id}</td>
                        <td style={{ fontSize: 13, color: 'var(--muted)' }}>{new Date(a.created_at).toLocaleString()}</td>
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
