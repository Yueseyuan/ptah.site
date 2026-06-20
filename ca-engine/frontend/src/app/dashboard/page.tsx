'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getDashboardStats } from '@/lib/api';

interface Stats {
  total_clients: number;
  active_cases: number;
  new_cases_this_week: number;
  pending_signatures: number;
  upcoming_appointments: number;
  invoiced_total: number;
  collected_total: number;
  pending_invoices: number;
  cases_by_division: Record<string, number>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content"><div className="spinner" /></main>
    </div>
  );

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Dashboard</h1>
          <p>Overview of all active operations — Cruel & Associates</p>
        </div>

        <div className="disclosure-banner">
          Cruel & Associates is not a law firm and does not provide legal advice or legal representation.
          All services are administrative document preparation only.
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <div className="label">Total Clients</div>
            <div className="value">{stats?.total_clients ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">Active Cases</div>
            <div className="value">{stats?.active_cases ?? 0}</div>
            <div className="sub">{stats?.new_cases_this_week ?? 0} new this week</div>
          </div>
          <div className="stat-card">
            <div className="label">Pending Signatures</div>
            <div className="value">{stats?.pending_signatures ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">Upcoming Appointments</div>
            <div className="value">{stats?.upcoming_appointments ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">Total Invoiced</div>
            <div className="value">${(stats?.invoiced_total ?? 0).toLocaleString()}</div>
            <div className="sub">${(stats?.collected_total ?? 0).toLocaleString()} collected</div>
          </div>
          <div className="stat-card">
            <div className="label">Pending Invoices</div>
            <div className="value">{stats?.pending_invoices ?? 0}</div>
          </div>
        </div>

        {stats?.cases_by_division && Object.keys(stats.cases_by_division).length > 0 && (
          <div className="card" style={{ marginTop: 8 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16, fontSize: 15 }}>Cases by Division</h3>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {Object.entries(stats.cases_by_division).map(([div, count]) => (
                <div key={div} style={{
                  background: 'var(--bg)', borderRadius: 8, padding: '12px 18px',
                  minWidth: 140, border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {div.replace('_', ' ')}
                  </div>
                  <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--navy)', marginTop: 4 }}>{count}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 12, fontSize: 15 }}>Quick Actions</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <a href="/clients/new" className="btn btn-primary btn-sm">+ New Client</a>
              <a href="/cases/new" className="btn btn-outline btn-sm">+ New Case</a>
              <a href="/appointments/new" className="btn btn-outline btn-sm">+ Schedule Appointment</a>
              <a href="/invoices/new" className="btn btn-outline btn-sm">+ Create Invoice</a>
            </div>
          </div>
          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 12, fontSize: 15 }}>Divisions</h3>
            <div style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 2 }}>
              <div>✍️ Notary Services</div>
              <div>📊 Credit Services</div>
              <div>🔓 Community Reentry</div>
              <div>📝 Document Preparation</div>
              <div>🏦 Asset Recovery</div>
              <div>🏢 Business Formation</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
