'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listReports, uploadReport, reparseReport, deleteReport } from '@/lib/api';

interface Report { id: number; bureau: string; parse_status: string; report_date: string; has_text: boolean; created_at: string; parse_error?: string; }

const BUREAUS = ['experian', 'equifax', 'transunion', 'innovis', 'all'];

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
      const result = await uploadReport(fd);
      if (result.parse_status === 'parsed') {
        setSuccess('Report uploaded and text extracted. If no tradelines appear, set ANTHROPIC_API_KEY in the backend .env file and reparse.');
      } else if (result.parse_status === 'failed') {
        setError(`Parse failed: ${result.parse_error || 'Unknown error'}`);
      } else {
        setSuccess('Report uploaded.');
      }
      if (fileRef.current) fileRef.current.value = '';
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Upload failed.');
    } finally { setUploading(false); }
  }

  async function reparse(reportId: number) {
    setError(''); setSuccess('');
    try {
      const result = await reparseReport(reportId);
      if (result.parse_status === 'failed') {
        setError(`Reparse failed: ${result.parse_error || 'Unknown error'}`);
      } else {
        setSuccess('Reparse complete. Check Tradelines tab for results.');
      }
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Reparse failed.');
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
        <div className="page-header"><h1>Credit Reports</h1><p>Upload bureau credit report PDFs</p></div>
        <CaseNav caseId={caseId} />

        <div className="alert-warning" style={{ marginBottom: 16 }}>
          <b>AI Parsing Required:</b> Tradeline extraction uses the Claude AI API.
          To enable: create a file at <code>aegis-credit/backend/.env</code> containing{' '}
          <code>ANTHROPIC_API_KEY=your_key_here</code>, then restart the backend and click <b>Reparse</b>.
          Get a key at <b>console.anthropic.com</b>.
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <h3>Upload New Report</h3>
          <div className="grid-2">
            <div className="form-group">
              <label>Bureau</label>
              <select value={bureau} onChange={e => setBureau(e.target.value)}>
                <option value="experian">Experian</option>
                <option value="equifax">Equifax</option>
                <option value="transunion">TransUnion</option>
                <option value="innovis">Innovis</option>
                <option value="all">All Bureaus (combined report)</option>
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
              <thead>
                <tr>
                  <th>Bureau</th>
                  <th>Status</th>
                  <th>Text Extracted</th>
                  <th>Uploaded</th>
                  <th>Error</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reports.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{r.bureau}</td>
                    <td>
                      <span className={`badge badge-${r.parse_status === 'parsed' ? 'success' : r.parse_status === 'failed' ? 'high' : 'pending'}`}>
                        {r.parse_status}
                      </span>
                    </td>
                    <td>{r.has_text ? <span style={{ color: 'var(--success)' }}>✓ Yes</span> : <span style={{ color: 'var(--muted)' }}>—</span>}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(r.created_at).toLocaleString()}</td>
                    <td style={{ color: 'var(--danger)', fontSize: 11, maxWidth: 280, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }} title={r.parse_error || ''}>{r.parse_error || ''}</td>
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

        <div className="card">
          <h3>No AI Key? Add Tradelines Manually</h3>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>
            Go to the <b>Tradelines</b> tab — you can view what was parsed. If empty, you can add tradelines manually from the Tradelines page after setting up your API key and reparsing.
          </p>
          <a href={`/cases/${caseId}/tradelines`} className="btn btn-outline btn-sm">Go to Tradelines</a>
        </div>
      </main>
    </div>
  );
}
