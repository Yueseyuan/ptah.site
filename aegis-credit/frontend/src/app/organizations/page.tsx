'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listOrganizations, createOrganization } from '@/lib/api';

interface Org {
  id: number;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  active: boolean;
  created_at: string;
}

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', address: '', phone: '', email: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function load() {
    listOrganizations().then(setOrgs).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createOrganization(form);
      setShowForm(false);
      setForm({ name: '', address: '', phone: '', email: '' });
      load();
    } catch {
      setError('Failed to create organization.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Organizations</h1>
            <p>Manage tenant organizations for multi-user access</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : '+ Add Organization'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 20 }}>
            <h3>New Organization</h3>
            {error && <div className="alert-error" style={{ marginBottom: 12 }}>{error}</div>}
            <form onSubmit={handleCreate}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Organization Name *</label>
                  <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Phone</label>
                  <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Address</label>
                  <input value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Create Organization'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? <div className="spinner" /> : orgs.length === 0 ? (
            <p className="empty">No organizations yet. Add the first one above.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map(o => (
                  <tr key={o.id}>
                    <td style={{ fontWeight: 600 }}>{o.name}</td>
                    <td style={{ color: 'var(--muted)' }}>{o.email || '—'}</td>
                    <td style={{ color: 'var(--muted)' }}>{o.phone || '—'}</td>
                    <td>
                      <span className={`badge ${o.active ? 'badge-active' : 'badge-closed'}`}>
                        {o.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {new Date(o.created_at).toLocaleDateString()}
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
