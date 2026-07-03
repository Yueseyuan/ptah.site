'use client';
import { useEffect, useState, useRef } from 'react';
import { portalDocuments, portalUploadDocument } from '@/lib/portal-api';

interface PortalDoc {
  id: number;
  doc_type: string;
  bureau: string | null;
  original_filename: string | null;
  notes: string | null;
  uploaded_at: string | null;
  reviewed: boolean;
}

const DOC_TYPES = [
  { value: 'credit_report_experian', label: 'Credit Report — Experian', bureau: 'Experian' },
  { value: 'credit_report_equifax', label: 'Credit Report — Equifax', bureau: 'Equifax' },
  { value: 'credit_report_transunion', label: 'Credit Report — TransUnion', bureau: 'TransUnion' },
  { value: 'drivers_license', label: "Driver's License / Government ID", bureau: null },
  { value: 'proof_of_address', label: 'Proof of Address', bureau: null },
  { value: 'supporting_doc', label: 'Supporting Document', bureau: null },
  { value: 'other', label: 'Other', bureau: null },
];

const TYPE_LABELS: Record<string, string> = Object.fromEntries(
  DOC_TYPES.map(d => [d.value, d.label])
);

export default function PortalDocumentsPage() {
  const [docs, setDocs] = useState<PortalDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [docType, setDocType] = useState('credit_report_experian');
  const [notes, setNotes] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function loadDocs() {
    portalDocuments().then(setDocs).catch(() => setError('Failed to load documents.')).finally(() => setLoading(false));
  }

  useEffect(() => { loadDocs(); }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) { setError('Please select a file.'); return; }
    setUploading(true);
    setError('');
    setSuccess('');
    try {
      const fd = new FormData();
      fd.append('doc_type', docType);
      fd.append('file', file);
      const selectedType = DOC_TYPES.find(d => d.value === docType);
      if (selectedType?.bureau) fd.append('bureau', selectedType.bureau);
      if (notes) fd.append('notes', notes);
      await portalUploadDocument(fd);
      const isCreditReport = docType.startsWith('credit_report');
      setSuccess(isCreditReport
        ? 'Credit report uploaded. We are extracting your tradelines and data automatically — this may take a moment.'
        : 'Document uploaded successfully.');
      setFile(null);
      setNotes('');
      if (fileRef.current) fileRef.current.value = '';
      loadDocs();
    } catch {
      setError('Upload failed. Please try again or contact your case manager.');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>Documents</h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Upload your credit reports and supporting documents. All files are stored securely.
        </p>
      </div>

      {/* Get Your Credit Reports */}
      <div style={{
        background: 'linear-gradient(135deg, #0a2540, #1a3a60)',
        border: '1px solid #1e3a5f', borderRadius: 12,
        padding: '20px 24px', marginBottom: 24, color: '#fff',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          <div style={{ fontSize: 28, flexShrink: 0 }}>📊</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
              Need to pull your credit reports?
            </div>
            <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.6, marginBottom: 14 }}>
              Use the link below to get all three bureau reports (Experian, Equifax &amp; TransUnion)
              through our partner — then download and upload them here. You&apos;ll need all three
              for us to begin your dispute process.
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <a
                href="https://app.myfreescorenow.com/enroll/B01B3951"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  background: '#c9a84c', color: '#07090f', fontWeight: 700,
                  fontSize: 13, padding: '8px 18px', borderRadius: 6,
                  textDecoration: 'none', display: 'inline-block',
                }}
              >
                Get My Free Credit Reports →
              </a>
              <a
                href="https://app.myfreescorenow.com/enroll/B02B3951"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  background: 'transparent', color: '#ccd6f6', fontWeight: 600,
                  fontSize: 13, padding: '8px 18px', borderRadius: 6,
                  textDecoration: 'none', display: 'inline-block',
                  border: '1px solid rgba(255,255,255,0.25)',
                }}
              >
                Alternate Link
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Form */}
      <div style={{
        background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
        padding: 24, marginBottom: 24,
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>
          Upload a Document
        </h3>

        {error && (
          <div style={{
            background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
            borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 14,
          }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{
            background: '#f0fdf4', color: '#166534', border: '1px solid #86efac',
            borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 14,
          }}>
            {success}
          </div>
        )}

        <form onSubmit={handleUpload}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Document Type *</label>
              <select
                value={docType}
                onChange={e => setDocType(e.target.value)}
                style={{ ...inputStyle, width: '100%' }}
                required
              >
                {DOC_TYPES.map(d => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>File *</label>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.heic,.tiff,.doc,.docx"
              onChange={e => setFile(e.target.files?.[0] || null)}
              required
              style={{
                display: 'block', width: '100%', padding: '9px 12px',
                border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13,
                background: '#f9fafb', boxSizing: 'border-box',
              }}
            />
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
              Accepted: PDF, JPG, PNG, HEIC, TIFF, DOC, DOCX
            </div>
          </div>

          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Notes (optional)</label>
            <input
              type="text"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="e.g. Experian report dated June 2025"
              style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
            />
          </div>

          <button type="submit" disabled={uploading} style={btnStyle}>
            {uploading ? 'Uploading…' : 'Upload Document'}
          </button>
        </form>
      </div>

      {/* Document List */}
      <div style={{
        background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 24,
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>
          Uploaded Documents ({docs.length})
        </h3>

        {loading ? (
          <div style={{ color: '#64748b', fontSize: 14, textAlign: 'center', padding: 24 }}>Loading…</div>
        ) : docs.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: '32px 0', color: '#94a3b8', fontSize: 14,
          }}>
            No documents uploaded yet. Use the form above to get started.
          </div>
        ) : (
          <div>
            {docs.map(doc => (
              <div key={doc.id} style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '12px 0', borderBottom: '1px solid #f1f5f9',
              }}>
                <div style={{
                  width: 40, height: 40, background: '#eff6ff', borderRadius: 8,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, flexShrink: 0,
                }}>
                  {fileIcon(doc.doc_type)}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 2 }}>
                    {TYPE_LABELS[doc.doc_type] || doc.doc_type}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.original_filename}
                    {doc.notes && <span style={{ marginLeft: 8, color: '#94a3b8' }}>— {doc.notes}</span>}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{
                    fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
                    background: doc.reviewed ? '#dcfce7' : '#f1f5f9',
                    color: doc.reviewed ? '#16a34a' : '#64748b',
                    marginBottom: 4,
                  }}>
                    {doc.reviewed ? 'Reviewed' : 'Pending Review'}
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>
                    {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 10,
        padding: '12px 16px', marginTop: 16, fontSize: 12, color: '#0c4a6e', lineHeight: 1.6,
      }}>
        <strong>Tip:</strong> Upload all three credit bureau reports (Experian, Equifax, TransUnion)
        plus a government-issued photo ID. Use the link above to pull all three reports at once.
      </div>
    </div>
  );
}

function fileIcon(docType: string): string {
  if (docType.startsWith('credit_report')) return '📊';
  if (docType === 'drivers_license') return '🪪';
  if (docType === 'proof_of_address') return '🏠';
  return '📄';
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5,
};
const inputStyle: React.CSSProperties = {
  padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8,
  fontSize: 14, outline: 'none', display: 'block',
};
const btnStyle: React.CSSProperties = {
  background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8,
  padding: '10px 24px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
};
