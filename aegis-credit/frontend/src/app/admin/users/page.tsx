'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listUsers, updateUser } from '@/lib/api';

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

const ROLES = ['admin', 'investigator', 'reviewer', 'readonly'];

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  function fetchUsers() {
    setLoading(true);
    listUsers()
      .then(setUsers)
      .catch(() => setError('Failed to load users. Admin access required.'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { fetchUsers(); }, []);

  async function handleRoleChange(id: number, role: string) {
    setSavingId(id);
    try {
      await updateUser(id, { role });
      setUsers(prev => prev.map(u => u.id === id ? { ...u, role } : u));
    } finally {
      setSavingId(null);
    }
  }

  async function handleToggleActive(id: number, is_active: boolean) {
    setSavingId(id);
    try {
      await updateUser(id, { is_active: !is_active });
      setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: !is_active } : u));
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>User Management</h1>
          <p>{users.length} user{users.length !== 1 ? 's' : ''} in system</p>
        </div>

        {loading && <div className="spinner" />}
        {error && <div style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</div>}

        {!loading && !error && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--surface-2, #f5f5f5)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Username</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Email</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Full Name</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Role</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Joined</th>
                  <th style={{ padding: '10px 14px', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.id} style={{ borderTop: i > 0 ? '1px solid var(--border)' : 'none' }}>
                    <td style={{ padding: '10px 14px', fontWeight: 500 }}>{u.username}</td>
                    <td style={{ padding: '10px 14px', color: 'var(--muted)' }}>{u.email}</td>
                    <td style={{ padding: '10px 14px' }}>{u.full_name || '—'}</td>
                    <td style={{ padding: '10px 14px' }}>
                      <select
                        value={u.role}
                        disabled={savingId === u.id}
                        onChange={e => handleRoleChange(u.id, e.target.value)}
                        style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid var(--border)', fontSize: 12 }}
                      >
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 12, fontSize: 11,
                        background: u.is_active ? 'var(--success-bg, #dcfce7)' : 'var(--danger-bg, #fee2e2)',
                        color: u.is_active ? 'var(--success, #16a34a)' : 'var(--danger, #dc2626)',
                      }}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--muted)', fontSize: 12 }}>
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <button
                        disabled={savingId === u.id}
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        style={{
                          padding: '4px 10px', fontSize: 12, borderRadius: 4, cursor: 'pointer',
                          border: '1px solid var(--border)',
                          background: u.is_active ? 'var(--danger-bg, #fee2e2)' : 'var(--success-bg, #dcfce7)',
                          color: u.is_active ? 'var(--danger, #dc2626)' : 'var(--success, #16a34a)',
                        }}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--muted)' }}>
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
