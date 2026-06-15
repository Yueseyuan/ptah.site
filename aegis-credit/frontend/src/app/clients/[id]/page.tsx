'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { getClient, listCourtRecordsByClient, createCourtRecord } from '@/lib/api';

interface Client { id: number; first_name: string; last_name: string; email: string; phone: string; address: string; city: string; state: string; zip_code: string; dob: string; ssn_last4: string; notes: string; created_at: string; }
interface CourtRecord { id: number; record_type: string; court_name: string; jurisdiction: string; docket_number: string; offense_date: string; disposition: string; expungement_eligible: boolean; }

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [client, setClient] = useState<Client | null>(null);
  const [records, setRecords] = useState<CourtRecord[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ record_type: 'criminal', court_name: '', jurisdiction: '', docket_number: '', offense_date: '', disposition: '', expungement_eligible: false, notes: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    const n = parseInt(id);
    getClient(n).then(setClient).catch(console.error);
    listCourtRecordsByClient(n).then(setRecords).catch(console.error);
  }, [id]);

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
          <Link href={`/cases/new?client_id=${client.id}`} className="btn btn-primary">+ New Case</Link>
        </div>

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
