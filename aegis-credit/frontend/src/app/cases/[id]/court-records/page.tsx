'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listCourtRecordsByCase, createCourtRecord, deleteCourtRecord, getCase } from '@/lib/api';

interface CourtRecord { id: number; record_type: string; court_name: string; jurisdiction: string; docket_number: string; offense_date: string; disposition: string; disposition_date: string; expungement_eligible: boolean; notes: string; }

export default function CourtRecordsPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [records, setRecords] = useState<CourtRecord[]>([]);
  const [clientId, setClientId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ record_type: 'criminal', court_name: '', jurisdiction: '', docket_number: '', offense_date: '', disposition: '', disposition_date: '', expungement_eligible: false, notes: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    getCase(caseId).then(c => setClientId(c.client_id));
    listCourtRecordsByCase(caseId).then(setRecords);
  }, [caseId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError('');
    if (!clientId) return;
    try {
      await createCourtRecord({ ...form, client_id: clientId, case_id: caseId });
      listCourtRecordsByCase(caseId).then(setRecords);
      setShowForm(false);
    } catch (err: unknown) { const e = err as { message?: string }; setError(e.message || 'Failed'); }
  }

  async function del(recordId: number) {
    if (!confirm('Delete this record?')) return;
    await deleteCourtRecord(recordId);
    listCourtRecordsByCase(caseId).then(setRecords);
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Court Records</h1><p>Criminal, civil, bankruptcy, judgment, and lien records</p></div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Record'}</button>
        </div>
        <CaseNav caseId={caseId} />

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add Court Record</h3>
            {error && <div className="alert-error">{error}</div>}
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group"><label>Type</label><select value={form.record_type} onChange={e => setForm(f => ({ ...f, record_type: e.target.value }))}>
                  <option value="criminal">Criminal</option><option value="civil">Civil</option><option value="bankruptcy">Bankruptcy</option><option value="judgment">Judgment</option><option value="lien">Lien</option>
                </select></div>
                <div className="form-group"><label>Court Name</label><input value={form.court_name} onChange={e => setForm(f => ({ ...f, court_name: e.target.value }))} /></div>
                <div className="form-group"><label>Jurisdiction</label><input value={form.jurisdiction} onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))} /></div>
                <div className="form-group"><label>Docket Number</label><input value={form.docket_number} onChange={e => setForm(f => ({ ...f, docket_number: e.target.value }))} /></div>
                <div className="form-group"><label>Offense Date</label><input type="date" value={form.offense_date} onChange={e => setForm(f => ({ ...f, offense_date: e.target.value }))} /></div>
                <div className="form-group"><label>Disposition</label><input value={form.disposition} onChange={e => setForm(f => ({ ...f, disposition: e.target.value }))} /></div>
                <div className="form-group"><label>Disposition Date</label><input type="date" value={form.disposition_date} onChange={e => setForm(f => ({ ...f, disposition_date: e.target.value }))} /></div>
              </div>
              <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12, fontWeight: 400 }}>
                <input type="checkbox" checked={form.expungement_eligible} onChange={e => setForm(f => ({ ...f, expungement_eligible: e.target.checked }))} style={{ width: 'auto' }} />
                Expungement Eligible
              </label>
              <div className="form-group"><label>Notes</label><textarea rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></div>
              <button type="submit" className="btn btn-primary btn-sm">Save Record</button>
            </form>
          </div>
        )}

        <div className="card">
          {records.length === 0 ? <p className="empty">No court records for this case.</p> : (
            <table>
              <thead><tr><th>Type</th><th>Court</th><th>Docket</th><th>Offense</th><th>Disposition</th><th>Expunge</th><th></th></tr></thead>
              <tbody>
                {records.map(r => (
                  <tr key={r.id}>
                    <td><span className="badge badge-pending">{r.record_type}</span></td>
                    <td>{r.court_name}</td>
                    <td><code>{r.docket_number}</code></td>
                    <td style={{ fontSize: 12 }}>{r.offense_date || '—'}</td>
                    <td>{r.disposition}</td>
                    <td>{r.expungement_eligible ? <span className="badge badge-success">Yes</span> : '—'}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => del(r.id)}>Delete</button></td>
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
