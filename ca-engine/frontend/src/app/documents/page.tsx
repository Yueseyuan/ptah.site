'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listDocuments, downloadDocumentUrl, updateDocumentStatus } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  draft: '#6b7280', generated: '#3b82f6', sent: '#f59e0b',
  signed: '#10b981', archived: '#9ca3af',
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setDocs(await listDocuments()); } finally { setLoading(false); }
  }

  async function archive(id: number) {
    await updateDocumentStatus(id, 'archived');
    await load();
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Documents</h1>
          <p>Generated documents across all cases — open a case to generate new documents</p>
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : docs.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
              No documents yet. Open a case and use the Generate Documents panel.
            </p>
          ) : (
            <table>
              <thead>
                <tr><th>Type</th><th>Case</th><th>Status</th><th>Date</th><th>Download</th><th></th></tr>
              </thead>
              <tbody>
                {docs.map((d: any) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 600 }}>{d.document_type?.replace(/_/g, ' ')}</td>
                    <td>Case #{d.case_id}</td>
                    <td>
                      <span style={{
                        background: STATUS_COLORS[d.status] || '#999', color: 'white',
                        borderRadius: 4, padding: '2px 8px', fontSize: 11,
                      }}>{d.status}</span>
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--muted)' }}>
                      {new Date(d.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <a href={downloadDocumentUrl(d.id, 'pdf')} target="_blank" className="btn btn-outline btn-sm">PDF</a>
                      <a href={downloadDocumentUrl(d.id, 'docx')} target="_blank" className="btn btn-outline btn-sm">DOCX</a>
                    </td>
                    <td>
                      {d.status !== 'archived' && (
                        <button onClick={() => archive(d.id)} className="btn btn-outline btn-sm">Archive</button>
                      )}
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
