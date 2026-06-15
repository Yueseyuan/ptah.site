'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listReports, uploadReport, reparseReport, deleteReport } from '@/lib/api';

interface Report { id: number; bureau: string; parse_status: string; report_date: string; has_text: boolean; created_at: string; parse_error?: string; }

const BUREAUS = ['experian', 'equifax', 'transunion', 'innovis'];

export default function ReportsPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [bureau, setBureau] = useState('experian');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  function load() { listReports(caseId).then(setReports).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function upload() {
    if (!fileRef.current?.files?.[0]) { setError('Select a PDF file.'); return; }
    setUploading(true); setError(''); setSuccess('');
    const fd = new FormData();
    fd.append('case_id', String(caseId));
    fd.append('bureau', bureau);
    fd.append('file', fileRef.current.files[0]);
    try {
      await uploadReport(fd);
      setSuccess('Report uploaded and parsed.');
      if (fileRef.current) fileRef.current.value = '';
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Upload failed.');
    } finally { setUploading(false); }
  }

  async function reparse(reportId: number) {
    try {
      await reparseReport(reportId);
      setSuccess('Reparse complete.');
      load();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Reparse failed.');
    }
  }

  async function del(reportId: number) {
    if (!confirm('Delete this report and all its tradelines?')) return;
    await deleteReport(reportId);
    load();
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header"><h1>Credit Reports</h1><p>Upload and manage bureau credit reports</p></div>
        <CaseNav caseId={caseId} />

        <div className="card" style={{ marginBottom: 16 }}>
          <h3>Upload New Report</h3>
          <div className="disclosure-banner">PDF files only. Text is extracted and tradelines are parsed via AI. No data is shared outside this system.</div>
          <div className="grid-2">
            <div className="form-group">
              <label>Bureau</label>
              <select value={bureau} onChange={e => setBureau(e.target.value)}>
                {BUREAUS.map(b => <option key={b} value={b}>{b.charAt(0).toUpperCase() + b.slice(1)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>PDF File</label>
              <input type="file" accept=".pdf" ref={fileRef} />
            </div>
          </div>
          {error && <div className="alert-error">{error}</div>}
          {success && <div className="alert-success">{success}</div>}
          <button className="btn btn-primary" onClick={upload} disabled={uploading}>
            {uploading ? 'Uploading & Parsing…' : 'Upload Report'}
          </button>
        </div>

        <div className="card">
          <h3>Uploaded Reports ({reports.length})</h3>
          {loading ? <div className="spinner" /> : reports.length === 0 ? (
            <p className="empty">No reports uploaded yet.</p>
          ) : (
            <table>
              <thead><tr><th>Bureau</th><th>Status</th><th>Has Text</th><th>Uploaded</th><th>Error</th><th></th></tr></thead>
              <tbody>
                {reports.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{r.bureau}</td>
                    <td><span className={`badge badge-${r.parse_status === 'parsed' ? 'success' : r.parse_status === 'failed' ? 'high' : 'pending'}`}>{r.parse_status}</span></td>
                    <td>{r.has_text ? '✓' : '—'}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(r.created_at).toLocaleString()}</td>
                    <td style={{ color: 'var(--danger)', fontSize: 11 }}>{r.parse_error ? r.parse_error.slice(0, 60) : ''}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-outline btn-sm" onClick={() => reparse(r.id)}>Reparse</button>
                      <button className="btn btn-danger btn-sm" onClick={() => del(r.id)}>Delete</button>
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
