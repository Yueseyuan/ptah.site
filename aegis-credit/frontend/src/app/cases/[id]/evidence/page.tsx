'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listEvidence, uploadEvidence, createEvidence, deleteEvidence } from '@/lib/api';

interface Evidence { id: number; evidence_type: string; title: string; description: string; source: string; collected_at: string; file_path: string; created_at: string; }

const TYPES = ['bureau_response', 'payment_record', 'correspondence', 'screenshot', 'legal_doc', 'other'];

export default function EvidencePage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [items, setItems] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', evidence_type: 'correspondence', source: '', collected_at: '', description: '' });
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  function load() { listEvidence(caseId).then(setItems).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError('');
    try {
      if (file) {
        const fd = new FormData();
        fd.append('title', form.title);
        fd.append('evidence_type', form.evidence_type);
        fd.append('source', form.source);
        fd.append('collected_at', form.collected_at);
        fd.append('description', form.description);
        fd.append('file', file);
        await uploadEvidence(caseId, fd);
      } else {
        await createEvidence({ ...form, case_id: caseId });
      }
      setForm({ title: '', evidence_type: 'correspondence', source: '', collected_at: '', description: '' });
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      setShowForm(false);
      load();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Failed to add evidence.');
    }
  }

  async function del(itemId: number) {
    if (!confirm('Delete this evidence item?')) return;
    await deleteEvidence(itemId);
    load();
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Evidence Vault</h1><p>Supporting documents, bureau responses, correspondence</p></div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Evidence'}</button>
        </div>
        <CaseNav caseId={caseId} />

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add Evidence</h3>
            {error && <div className="alert-error">{error}</div>}
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group"><label>Title *</label><input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
                <div className="form-group"><label>Type</label><select value={form.evidence_type} onChange={e => setForm(f => ({ ...f, evidence_type: e.target.value }))}>
                  {TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </select></div>
                <div className="form-group"><label>Source</label><input value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} placeholder="e.g., Equifax, CFPB, creditor" /></div>
                <div className="form-group"><label>Collected Date</label><input type="date" value={form.collected_at} onChange={e => setForm(f => ({ ...f, collected_at: e.target.value }))} /></div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}><label>Description</label><textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}><label>File (optional)</label><input type="file" ref={fileRef} onChange={e => setFile(e.target.files?.[0] || null)} /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">Save</button>
            </form>
          </div>
        )}

        <div className="card">
          <h3>Evidence Items ({items.length})</h3>
          {loading ? <div className="spinner" /> : items.length === 0 ? (
            <p className="empty">No evidence logged yet.</p>
          ) : (
            <table>
              <thead><tr><th>Title</th><th>Type</th><th>Source</th><th>Collected</th><th>File</th><th>Added</th><th></th></tr></thead>
              <tbody>
                {items.map(i => (
                  <tr key={i.id}>
                    <td style={{ fontWeight: 600 }}>{i.title}</td>
                    <td><span className="badge badge-pending">{i.evidence_type}</span></td>
                    <td>{i.source || '—'}</td>
                    <td style={{ fontSize: 12 }}>{i.collected_at || '—'}</td>
                    <td>{i.file_path ? <code style={{ fontSize: 11 }}>✓ file</code> : '—'}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(i.created_at).toLocaleDateString()}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => del(i.id)}>Delete</button></td>
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
