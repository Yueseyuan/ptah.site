'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listPendingPortalCases, updatePortalCaseStatus } from '@/lib/api';

interface PortalIntake {
  case_id: number;
  case_number: string;
  portal_status: string;
  client_id: number | null;
  client_name: string;
  client_email: string;
  client_state: string;
  documents_uploaded: number;
  created_at: string;
}

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending Review', color: '#92400e', bg: '#fef9c3' },
  { value: 'docs_needed', label: 'Docs Needed', color: '#9a3412', bg: '#fff7ed' },
  { value: 'under_review', label: 'Under Review', color: '#1e3a8a', bg: '#eff6ff' },
  { value: 'active', label: 'Active', color: '#14532d', bg: '#f0fdf4' },
  { value: 'completed', label: 'Completed', color: '#374151', bg: '#f9fafb' },
];

function statusStyle(s: string) {
  const found = STATUS_OPTIONS.find(o => o.value === s);
  return found ? { background: found.bg, color: found.color } : { background: '#f3f4f6', color: '#374151' };
}

export default function PortalIntakePage() {
  const [cases, setCases] = useState<PortalIntake[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<number | null>(null);
  const [filter, setFilter] = useState('all');

  function load() {
    setLoading(true);
    listPendingPortalCases('all').then(setCases).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleStatusChange(caseId: number, status: string) {
    setUpdating(caseId);
    try {
      await updatePortalCaseStatus(caseId, status);
      setCases(prev => prev.map(c => c.case_id === caseId ? { ...c, portal_status: status } : c));
    } finally {
      setUpdating(null);
    }
  }

  const visible = filter === 'all' ? cases : cases.filter(c => c.portal_status === filter);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Portal Intake</h1>
            <p>{cases.length} client{cases.length !== 1 ? 's' : ''} registered via portal</p>
          </div>
          <button className="btn btn-outline" onClick={load}>Refresh</button>
        </div>

        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[{ value: 'all', label: 'All' }, ...STATUS_OPTIONS].map(opt => (
            <button
              key={opt.value}
              onClick={() => setFilter(opt.value)}
              style={{
                padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                border: filter === opt.value ? '2px solid #0a2540' : '1px solid #e2e8f0',
                background: filter === opt.value ? '#0a2540' : '#fff',
                color: filter === opt.value ? '#fff' : '#374151',
                cursor: 'pointer',
              }}
            >
              {opt.label} ({opt.value === 'all' ? cases.length : cases.filter(c => c.portal_status === opt.value).length})
            </button>
          ))}
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : visible.length === 0 ? (
            <p className="empty">No {filter === 'all' ? '' : filter} portal registrations.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Case #</th>
                  <th>State</th>
                  <th>Docs</th>
                  <th>Registered</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visible.map(c => (
                  <tr key={c.case_id}>
                    <td style={{ fontWeight: 600 }}>
                      <div>
                        {c.client_id
                          ? <Link href={`/clients/${c.client_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>{c.client_name}</Link>
                          : c.client_name
                        }
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 400 }}>{c.client_email}</div>
                    </td>
                    <td><code style={{ fontSize: 12 }}>{c.case_number}</code></td>
                    <td>{c.client_state || '—'}</td>
                    <td>
                      <span style={{
                        fontWeight: 700, fontSize: 13,
                        color: c.documents_uploaded >= 3 ? 'var(--success)' : c.documents_uploaded > 0 ? 'var(--warning)' : 'var(--muted)',
                      }}>
                        {c.documents_uploaded}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--muted)', marginLeft: 4 }}>/ 3 req</span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td>
                      <span style={{
                        ...statusStyle(c.portal_status),
                        padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                        display: 'inline-block',
                      }}>
                        {STATUS_OPTIONS.find(o => o.value === c.portal_status)?.label || c.portal_status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <select
                          value={c.portal_status}
                          disabled={updating === c.case_id}
                          onChange={e => handleStatusChange(c.case_id, e.target.value)}
                          style={{
                            padding: '4px 8px', borderRadius: 4,
                            border: '1px solid var(--border)', fontSize: 12, cursor: 'pointer',
                          }}
                        >
                          {STATUS_OPTIONS.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                        {c.client_id && (
                          <Link href={`/clients/${c.client_id}`} className="btn btn-outline btn-sm">
                            Client
                          </Link>
                        )}
                        <Link href={`/cases/${c.case_id}`} className="btn btn-outline btn-sm">
                          Case
                        </Link>
                      </div>
                    </td>
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
