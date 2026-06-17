'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { getClient, updateClient, listCourtRecordsByClient, createCourtRecord, getCasesByClient } from '@/lib/api';

interface Client { id: number; first_name: string; last_name: string; email: string; phone: string; address: string; city: string; state: string; zip_code: string; dob: string; ssn_last4: string; notes: string; created_at: string; }
interface CourtRecord { id: number; record_type: string; court_name: string; jurisdiction: string; docket_number: string; offense_date: string; disposition: string; expungement_eligible: boolean; }
interface Case { id: number; case_number: string; status: string; goal: string; created_at: string; }

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [client, setClient] = useState<Client | null>(null);
  const [records, setRecords] = useState<CourtRecord[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ record_type: 'criminal', court_name: '', jurisdiction: '', docket_number: '', offense_date: '', disposition: '', expungement_eligible: false, notes: '' });
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ first_name: '', last_name: '', email: '', phone: '', address: '', city: '', state: '', zip_code: '', dob: '', ssn_last4: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const n = parseInt(id);
    getClient(n).then(setClient).catch(console.error);
    listCourtRecordsByClient(n).then(setRecords).catch(console.error);
    getCasesByClient(n).then(setCases).catch(console.error);
  }, [id]);

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      const updated = await updateClient(parseInt(id), editForm);
      setClient(updated);
      setEditing(false);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Failed to save.');
    } finally { setSaving(false); }
  }

  async function addRecord(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await createCourtRecord({ ...form, client_id: parseInt(id) });
      listCourtRecordsByClient(parseInt(id)).then(setRecords);
      setShowForm(false);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Failed');
    }
  }

  if (!client) return <div className="main-layout"><Sidebar /><main className="main-content"><div className="spinner" /></main></div>;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>{client.first_name} {client.last_name}</h1>
            <p>Client #{client.id} · Added {new Date(client.created_at).toLocaleDateString()}</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-outline btn-sm" onClick={() => { if (!editing) setEditForm({ first_name: client.first_name, last_name: client.last_name, email: client.email, phone: client.phone, address: client.address, city: client.city, state: client.state, zip_code: client.zip_code, dob: client.dob, ssn_last4: client.ssn_last4, notes: client.notes }); setEditing(e => !e); setError(''); }}>
              {editing ? 'Cancel' : 'Edit Client'}
            </button>
            <Link href="/clients" className="btn btn-outline btn-sm">← Clients</Link>
          </div>
        </div>

        {editing && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Edit Client</h3>
            {error && <div className="alert-error">{error}</div>}
            <form onSubmit={handleEdit}>
              <div className="grid-2">
                <div className="form-group"><label>First Name</label><input value={editForm.first_name} onChange={e => setEditForm(f => ({ ...f, first_name: e.target.value }))} /></div>
                <div className="form-group"><label>Last Name</label><input value={editForm.last_name} onChange={e => setEditForm(f => ({ ...f, last_name: e.target.value }))} /></div>
                <div className="form-group"><label>Email</label><input type="email" value={editForm.email} onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))} /></div>
                <div className="form-group"><label>Phone</label><input value={editForm.phone} onChange={e => setEditForm(f => ({ ...f, phone: e.target.value }))} /></div>
                <div className="form-group"><label>Address</label><input value={editForm.address} onChange={e => setEditForm(f => ({ ...f, address: e.target.value }))} /></div>
                <div className="form-group"><label>City</label><input value={editForm.city} onChange={e => setEditForm(f => ({ ...f, city: e.target.value }))} /></div>
                <div className="form-group"><label>State</label><input value={editForm.state} onChange={e => setEditForm(f => ({ ...f, state: e.target.value }))} /></div>
                <div className="form-group"><label>ZIP Code</label><input value={editForm.zip_code} onChange={e => setEditForm(f => ({ ...f, zip_code: e.target.value }))} /></div>
                <div className="form-group"><label>Date of Birth</label><input type="date" value={editForm.dob} onChange={e => setEditForm(f => ({ ...f, dob: e.target.value }))} /></div>
                <div className="form-group"><label>SSN Last 4</label><input value={editForm.ssn_last4} onChange={e => setEditForm(f => ({ ...f, ssn_last4: e.target.value }))} maxLength={4} /></div>
              </div>
              <div className="form-group"><label>Notes</label><textarea value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))} rows={3} /></div>
              <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
            </form>
          </div>
        )}

        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card">
            <h3>Contact</h3>
            <p><b>Email:</b> {client.email || '—'}</p>
            <p><b>Phone:</b> {client.phone || '—'}</p>
            <p><b>DOB:</b> {client.dob || '—'}</p>
            <p><b>SSN:</b> {client.ssn_last4 ? `xxx-xx-${client.ssn_last4}` : '—'}</p>
          </div>
          <div className="card">
            <h3>Address</h3>
            <p>{client.address || '—'}</p>
            <p>{[client.city, client.state, client.zip_code].filter(Boolean).join(', ')}</p>
            {client.notes && <><br /><p style={{ color: 'var(--muted)', fontSize: 12 }}>{client.notes}</p></>}
          </div>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ marginBottom: 0 }}>Cases ({cases.length})</h3>
            <Link href={`/cases/new?client_id=${client.id}`} className="btn btn-outline btn-sm">+ New Case</Link>
          </div>
          {cases.length === 0 ? (
            <p className="empty">No cases yet. <Link href={`/cases/new?client_id=${client.id}`}>Create the first case.</Link></p>
          ) : (
            <table>
              <thead><tr><th>Case #</th><th>Status</th><th>Goal</th><th>Opened</th><th></th></tr></thead>
              <tbody>
                {cases.map(c => (
                  <tr key={c.id}>
                    <td><code>{c.case_number}</code></td>
                    <td><span className={`badge badge-${c.status === 'active' ? 'success' : c.status === 'closed' ? 'pending' : 'medium'}`}>{c.status.replace('_', ' ')}</span></td>
                    <td style={{ fontSize: 12, color: 'var(--muted)', maxWidth: 300 }}>{c.goal || '—'}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td><Link href={`/cases/${c.id}`} className="btn btn-outline btn-sm">Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ marginBottom: 0 }}>Court Records</h3>
            <button className="btn btn-outline btn-sm" onClick={() => setShowForm(s => !s)}>
              {showForm ? 'Cancel' : '+ Add Record'}
            </button>
          </div>
          {showForm && (
            <form onSubmit={addRecord} style={{ marginBottom: 16, padding: 16, background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
              {error && <div className="alert-error">{error}</div>}
              <div className="grid-2">
                <div className="form-group"><label>Record Type</label><select value={form.record_type} onChange={e => setForm(f => ({ ...f, record_type: e.target.value }))}>
                  <option value="criminal">Criminal</option><option value="civil">Civil</option><option value="bankruptcy">Bankruptcy</option><option value="judgment">Judgment</option><option value="lien">Lien</option>
                </select></div>
                <div className="form-group"><label>Court Name</label><input value={form.court_name} onChange={e => setForm(f => ({ ...f, court_name: e.target.value }))} /></div>
                <div className="form-group"><label>Jurisdiction</label><input value={form.jurisdiction} onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))} /></div>
                <div className="form-group"><label>Docket Number</label><input value={form.docket_number} onChange={e => setForm(f => ({ ...f, docket_number: e.target.value }))} /></div>
                <div className="form-group"><label>Offense Date</label><input type="date" value={form.offense_date} onChange={e => setForm(f => ({ ...f, offense_date: e.target.value }))} /></div>
                <div className="form-group"><label>Disposition</label><input value={form.disposition} onChange={e => setForm(f => ({ ...f, disposition: e.target.value }))} /></div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <input type="checkbox" checked={form.expungement_eligible} onChange={e => setForm(f => ({ ...f, expungement_eligible: e.target.checked }))} style={{ width: 'auto' }} />
                Expungement Eligible
              </label>
              <button type="submit" className="btn btn-primary btn-sm">Save Record</button>
            </form>
          )}
          {records.length === 0 ? <p className="empty">No court records.</p> : (
            <table>
              <thead><tr><th>Type</th><th>Court</th><th>Docket</th><th>Offense Date</th><th>Disposition</th><th>Expungement</th></tr></thead>
              <tbody>
                {records.map(r => (
                  <tr key={r.id}>
                    <td><span className="badge badge-pending">{r.record_type}</span></td>
                    <td>{r.court_name}</td>
                    <td><code>{r.docket_number}</code></td>
                    <td>{r.offense_date}</td>
                    <td>{r.disposition}</td>
                    <td>{r.expungement_eligible ? <span className="badge badge-success">Eligible</span> : <span className="badge">No</span>}</td>
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
