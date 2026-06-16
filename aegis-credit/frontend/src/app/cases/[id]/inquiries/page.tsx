'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listInquiries, createInquiry, deleteInquiry, analyzeInquiries } from '@/lib/api';

interface Inquiry {
  id: number;
  bureau: string;
  inquiry_type: string;
  subscriber_name: string;
  inquiry_date: string;
  purpose: string;
}

interface InqFinding {
  id?: number;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
}

const SEV_COLOR: Record<string, { bg: string; text: string }> = {
  high: { bg: '#fee2e2', text: '#991b1b' },
  medium: { bg: '#fef3c7', text: '#92400e' },
  low: { bg: '#dbeafe', text: '#1e40af' },
};

export default function InquiriesPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [findings, setFindings] = useState<InqFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subscriber_name: '', bureau: 'experian', inquiry_type: 'hard', inquiry_date: '', purpose: '' });

  function load() {
    listInquiries(caseId).then(setInquiries).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, [caseId]);

  async function analyze() {
    setAnalyzing(true); setError(''); setSuccess('');
    try {
      const r = await analyzeInquiries(caseId);
      setFindings(r.findings || []);
      setSuccess(`Analysis complete: ${r.findings_generated} finding(s) from ${r.inquiries_analyzed} inquiries.`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Analysis failed.');
    } finally { setAnalyzing(false); }
  }

  async function handleAdd() {
    try {
      await createInquiry({ ...form, case_id: caseId });
      setForm({ subscriber_name: '', bureau: 'experian', inquiry_type: 'hard', inquiry_date: '', purpose: '' });
      setShowForm(false);
      load();
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || 'Failed to add inquiry.');
    }
  }

  async function handleDelete(inqId: number) {
    if (!confirm('Delete this inquiry?')) return;
    await deleteInquiry(inqId);
    load();
  }

  const bureaus = [...new Set(inquiries.map(i => i.bureau))].sort();

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Inquiries</h1>
            <p>Credit inquiries grouped by bureau with pattern analysis</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => setShowForm(!showForm)}>+ Add Inquiry</button>
            <button className="btn btn-primary" onClick={analyze} disabled={analyzing || inquiries.length === 0}>
              {analyzing ? 'Analyzing…' : '🔍 Analyze Inquiries'}
            </button>
          </div>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginTop: 0, fontSize: 15 }}>Add Inquiry</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Subscriber Name *</label>
                <input className="form-input" value={form.subscriber_name} onChange={e => setForm(f => ({ ...f, subscriber_name: e.target.value }))} placeholder="Bank of America" />
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Bureau</label>
                <select className="form-input" value={form.bureau} onChange={e => setForm(f => ({ ...f, bureau: e.target.value }))}>
                  <option value="experian">Experian</option>
                  <option value="equifax">Equifax</option>
                  <option value="transunion">TransUnion</option>
                  <option value="innovis">Innovis</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Type</label>
                <select className="form-input" value={form.inquiry_type} onChange={e => setForm(f => ({ ...f, inquiry_type: e.target.value }))}>
                  <option value="hard">Hard</option>
                  <option value="soft">Soft</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Date</label>
                <input className="form-input" type="date" value={form.inquiry_date} onChange={e => setForm(f => ({ ...f, inquiry_date: e.target.value }))} />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Purpose</label>
                <input className="form-input" value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} placeholder="Auto loan" />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button className="btn btn-primary" onClick={handleAdd}>Save</button>
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        )}

        {loading ? (
          <p>Loading inquiries…</p>
        ) : inquiries.length === 0 ? (
          <div className="card">
            <p style={{ color: '#6b7280' }}>No inquiries found. Upload and parse credit reports or add inquiries manually.</p>
          </div>
        ) : (
          bureaus.map(bureau => {
            const bInquiries = inquiries.filter(i => i.bureau === bureau);
            const hard = bInquiries.filter(i => i.inquiry_type === 'hard');
            const soft = bInquiries.filter(i => i.inquiry_type === 'soft');
            return (
              <div key={bureau} className="card" style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h3 style={{ margin: 0, fontSize: 15, textTransform: 'capitalize' }}>{bureau}</h3>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <span style={{ background: '#fee2e2', color: '#991b1b', borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 600 }}>Hard: {hard.length}</span>
                    <span style={{ background: '#f3f4f6', color: '#374151', borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 600 }}>Soft: {soft.length}</span>
                  </div>
                </div>
                {hard.length > 0 && (
                  <>
                    <p style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Hard Inquiries</p>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginBottom: 12 }}>
                      <thead><tr style={{ background: '#f9fafb' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Subscriber</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Date</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Purpose</th>
                        <th style={{ padding: '6px 10px', borderBottom: '1px solid #e5e7eb' }}></th>
                      </tr></thead>
                      <tbody>{hard.map(inq => (
                        <tr key={inq.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                          <td style={{ padding: '6px 10px' }}>{inq.subscriber_name}</td>
                          <td style={{ padding: '6px 10px' }}>{inq.inquiry_date || '—'}</td>
                          <td style={{ padding: '6px 10px', color: '#6b7280' }}>{inq.purpose || '—'}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <button onClick={() => handleDelete(inq.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 12 }}>Delete</button>
                          </td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </>
                )}
                {soft.length > 0 && (
                  <>
                    <p style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Soft Inquiries</p>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead><tr style={{ background: '#f9fafb' }}>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Subscriber</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Date</th>
                        <th style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>Purpose</th>
                        <th style={{ padding: '6px 10px', borderBottom: '1px solid #e5e7eb' }}></th>
                      </tr></thead>
                      <tbody>{soft.map(inq => (
                        <tr key={inq.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                          <td style={{ padding: '6px 10px' }}>{inq.subscriber_name}</td>
                          <td style={{ padding: '6px 10px' }}>{inq.inquiry_date || '—'}</td>
                          <td style={{ padding: '6px 10px', color: '#6b7280' }}>{inq.purpose || '—'}</td>
                          <td style={{ padding: '6px 10px' }}>
                            <button onClick={() => handleDelete(inq.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 12 }}>Delete</button>
                          </td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </>
                )}
              </div>
            );
          })
        )}

        {findings.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Inquiry Analysis Findings</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {findings.map((f, i) => {
                const colors = SEV_COLOR[f.severity] || { bg: '#f3f4f6', text: '#374151' };
                return (
                  <div key={i} className="card" style={{ borderLeft: `4px solid ${colors.text}` }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                      <span style={{ background: '#1e40af', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, fontFamily: 'monospace' }}>{f.rule_code}</span>
                      <span style={{ background: colors.bg, color: colors.text, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' }}>{f.severity}</span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{f.rule_name}</span>
                    </div>
                    <p style={{ margin: '0 0 6px', fontSize: 13, color: '#374151' }}>{f.description}</p>
                    {f.fcra_section && <p style={{ margin: 0, fontSize: 11, color: '#6b7280' }}>FCRA Reference: {f.fcra_section}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
