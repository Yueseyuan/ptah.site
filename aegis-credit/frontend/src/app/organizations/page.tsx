'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listOrganizations, createOrganization, updateOrganization } from '@/lib/api';

interface Org { id: number; name: string; address: string | null; phone: string | null; email: string | null; active: boolean; created_at: string; }
type EditForm = { name: string; email: string; phone: string; address: string; };

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', address: '', phone: '', email: '' });
  const [creating, setCreating] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ name: '', email: '', phone: '', address: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() { listOrganizations().then(setOrgs).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true); setError('');
    try {
      await createOrganization(createForm);
      setShowCreate(false);
      setCreateForm({ name: '', address: '', phone: '', email: '' });
      setSuccess('Organization created.');
      load();
    } catch { setError('Failed to create organization.'); }
    finally { setCreating(false); }
  }

  function startEdit(o: Org) {
    setEditId(o.id);
    setEditForm({ name: o.name, email: o.email || '', phone: o.phone || '', address: o.address || '' });
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editId) return;
    setSaving(true); setError('');
    try {
      await updateOrganization(editId, editForm);
      setEditId(null);
      setSuccess('Organization updated.');
      load();
    } catch { setError('Failed to update organization.'); }
    finally { setSaving(false); }
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
          <button className="btn btn-primary" onClick={() => setShowCreate(s => !s)}>
            {showCreate ? 'Cancel' : '+ Add Organization'}
          </button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div>}
        {success && <div className="alert alert-success" style={{ marginBottom: 12 }}>{success}</div>}

        {showCreate && (
          <div className="card" style={{ marginBottom: 20 }}>
            <h3>New Organization</h3>
            <form onSubmit={handleCreate}>
              <div className="grid-2">
                <div className="form-group"><label>Organization Name *</label><input value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} required /></div>
                <div className="form-group"><label>Email</label><input type="email" value={createForm.email} onChange={e => setCreateForm(f => ({ ...f, email: e.target.value }))} /></div>
                <div className="form-group"><label>Phone</label><input value={createForm.phone} onChange={e => setCreateForm(f => ({ ...f, phone: e.target.value }))} /></div>
                <div className="form-group"><label>Address</label><input value={createForm.address} onChange={e => setCreateForm(f => ({ ...f, address: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={creating}>{creating ? 'Creating…' : 'Create Organization'}</button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? <div className="spinner" /> : orgs.length === 0 ? (
            <p className="empty">No organizations yet. Add the first one above.</p>
          ) : (
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Address</th><th>Status</th><th>Created</th><th></th></tr></thead>
              <tbody>
                {orgs.flatMap(o => {
                  const rows = [(
                    <tr key={o.id}>
                      <td style={{ fontWeight: 600 }}>{o.name}</td>
                      <td style={{ color: 'var(--muted)' }}>{o.email || '—'}</td>
                      <td style={{ color: 'var(--muted)' }}>{o.phone || '—'}</td>
                      <td style={{ color: 'var(--muted)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.address || '—'}</td>
                      <td><span className={`badge ${o.active ? 'badge-active' : 'badge-closed'}`}>{o.active ? 'Active' : 'Inactive'}</span></td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(o.created_at).toLocaleDateString()}</td>
                      <td>
                        <button className="btn btn-outline btn-sm" onClick={() => editId === o.id ? setEditId(null) : startEdit(o)}>
                          {editId === o.id ? 'Cancel' : 'Edit'}
                        </button>
                      </td>
                    </tr>
                  )];
                  if (editId === o.id) {
                    rows.push(
                      <tr key={`edit-${o.id}`}>
                        <td colSpan={7} style={{ padding: '12px 16px', background: '#f8fafc' }}>
                          <form onSubmit={handleEdit}>
                            <div className="grid-2" style={{ marginBottom: 10 }}>
                              <div className="form-group"><label>Name *</label><input required value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} /></div>
                              <div className="form-group"><label>Email</label><input type="email" value={editForm.email} onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))} /></div>
                              <div className="form-group"><label>Phone</label><input value={editForm.phone} onChange={e => setEditForm(f => ({ ...f, phone: e.target.value }))} /></div>
                              <div className="form-group"><label>Address</label><input value={editForm.address} onChange={e => setEditForm(f => ({ ...f, address: e.target.value }))} /></div>
                            </div>
                            <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
                          </form>
                        </td>
                      </tr>
                    );
                  }
                  return rows;
                })}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
