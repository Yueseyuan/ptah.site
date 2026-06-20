'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { getCase, updateCase, listDocuments, generateDocument, downloadDocumentUrl } from '@/lib/api';

const STATUSES = ['intake', 'in_progress', 'completed', 'closed'];
const DOC_TYPES: Record<string, string[]> = {
  notary: ['notarial_certificate', 'notary_journal'],
  credit: ['dispute_letter', 'credit_summary'],
  reentry: ['reentry_plan', 'support_letter'],
  document_prep: ['prepared_document', 'cover_letter'],
  asset_recovery: ['demand_letter', 'asset_summary'],
  business_formation: ['articles_of_incorporation', 'operating_agreement'],
};

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [caseData, setCaseData] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => { load(); }, [id]);

  async function load() {
    setLoading(true);
    try {
      const [c, d] = await Promise.all([getCase(Number(id)), listDocuments({ case_id: id })]);
      setCaseData(c);
      setDocs(d);
    } finally { setLoading(false); }
  }

  async function changeStatus(status: string) {
    await updateCase(Number(id), { status });
    setCaseData((p: any) => ({ ...p, status }));
  }

  async function generate(docType: string) {
    setGenerating(true);
    setMsg('');
    try {
      await generateDocument(Number(id), docType);
      setMsg('Document generated.');
      const d = await listDocuments({ case_id: id });
      setDocs(d);
    } catch { setMsg('Generation failed.'); } finally { setGenerating(false); }
  }

  if (loading) return (
    <div className="main-layout"><Sidebar /><main className="main-content"><div className="spinner" /></main></div>
  );
  if (!caseData) return (
    <div className="main-layout"><Sidebar /><main className="main-content"><p>Case not found.</p></main></div>
  );

  const availableDocs = DOC_TYPES[caseData.division] || [];

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>{caseData.title}</h1>
            <p>
              <Link href={`/clients/${caseData.client_id}`}>Client #{caseData.client_id}</Link>
              {' · '}{caseData.division}{' · '}
              {new Date(caseData.created_at).toLocaleDateString()}
            </p>
          </div>
          <button onClick={() => router.back()} className="btn btn-outline">Back</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 14, fontSize: 15 }}>Case Details</h3>
            {caseData.description && <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>{caseData.description}</p>}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: 'var(--muted)', display: 'block', marginBottom: 6 }}>Status</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {STATUSES.map((s) => (
                  <button key={s} onClick={() => changeStatus(s)}
                    className={caseData.status === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}>
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 14, fontSize: 15 }}>Generate Documents</h3>
            {availableDocs.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>No templates for this division.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {availableDocs.map((dt) => (
                  <button key={dt} onClick={() => generate(dt)} disabled={generating}
                    className="btn btn-outline btn-sm" style={{ textAlign: 'left' }}>
                    {generating ? 'Generating…' : dt.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            )}
            {msg && <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>{msg}</p>}
          </div>
        </div>

        <div className="card">
          <h3 style={{ color: 'var(--navy)', marginBottom: 14, fontSize: 15 }}>Documents ({docs.length})</h3>
          {docs.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 24 }}>No documents yet. Generate one above.</p>
          ) : (
            <table>
              <thead><tr><th>Type</th><th>Status</th><th>Date</th><th>Download</th></tr></thead>
              <tbody>
                {docs.map((d: any) => (
                  <tr key={d.id}>
                    <td>{d.document_type?.replace(/_/g, ' ')}</td>
                    <td>{d.status}</td>
                    <td style={{ fontSize: 13, color: 'var(--muted)' }}>{new Date(d.created_at).toLocaleDateString()}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <a href={downloadDocumentUrl(d.id, 'pdf')} target="_blank" className="btn btn-outline btn-sm">PDF</a>
                      <a href={downloadDocumentUrl(d.id, 'docx')} target="_blank" className="btn btn-outline btn-sm">DOCX</a>
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
