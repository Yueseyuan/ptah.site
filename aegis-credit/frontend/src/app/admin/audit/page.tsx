'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listAllAudit } from '@/lib/api';

interface AuditEntry {
  id: number;
  username: string;
  action: string;
  resource_type: string;
  resource_id: number | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
}

const ACTION_TYPES = ['', 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'AI_GENERATE', 'APPROVE_FINDING', 'ANALYZE'];

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterAction, setFilterAction] = useState('');

  useEffect(() => {
    listAllAudit()
      .then(setEntries)
      .catch(() => setError('Failed to load audit log. Admin access required.'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filterAction
    ? entries.filter(e => e.action === filterAction)
    : entries;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1>Audit Log</h1>
            <p>For compliance purposes. This log is immutable.</p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label style={{ fontSize: 13, color: 'var(--muted)' }}>Filter by action:</label>
            <select
              value={filterAction}
              onChange={e => setFilterAction(e.target.value)}
              style={{ fontSize: 13, padding: '4px 8px', borderRadius: 4, border: '1px solid var(--border)' }}
            >
              {ACTION_TYPES.map(a => (
                <option key={a} value={a}>{a || 'All Actions'}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <div className="alert-error">{error}</div>}

        {loading ? <div className="spinner" /> : (
          <div className="card">
            {filtered.length === 0 ? (
              <p className="empty">No audit log entries found.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource Type</th>
                    <th>Resource ID</th>
                    <th>Detail</th>
                    <th>IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(e => (
                    <tr key={e.id}>
                      <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>{e.created_at ? new Date(e.created_at).toLocaleString() : '—'}</td>
                      <td><code style={{ fontSize: 12 }}>{e.username || '—'}</code></td>
                      <td><span className="badge badge-pending">{e.action}</span></td>
                      <td style={{ fontSize: 12 }}>{e.resource_type}</td>
                      <td style={{ fontSize: 12 }}>{e.resource_id ?? '—'}</td>
                      <td style={{ fontSize: 12, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.detail || '—'}</td>
                      <td style={{ fontSize: 12 }}>{e.ip_address || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
