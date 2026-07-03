'use client';
import { useEffect, useState, useCallback, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ServiceCase {
  id: number;
  case_number: string;
  division_slug: string;
  status: string;
  client_name: string | null;
  client_id: number;
  notes: string | null;
  intake_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface Document {
  id: number;
  title: string;
  document_type: string;
  status: string;
  ai_generated: boolean;
  created_at: string;
}

interface Appointment {
  id: number;
  appointment_type: string;
  scheduled_at: string;
  location?: string;
  status: string;
  notes?: string;
}

interface Invoice {
  id: number;
  invoice_number: string;
  total: number;
  status: string;
  due_date?: string;
  created_at: string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const DIVISION_LABELS: Record<string, string> = {
  notary: 'Mobile Notary',
  credit: 'Credit Restoration',
  criminal: 'Criminal Record Relief',
  document: 'Document Preparation',
  judgment: 'Judgment & Asset Recovery',
  consulting: 'Business Consulting',
};

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6',
  active: '#10b981',
  on_hold: '#f59e0b',
  closed: '#6b7280',
};

const STATUSES = ['intake', 'active', 'on_hold', 'closed'];

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'documents', label: 'Documents' },
  { id: 'appointments', label: 'Appointments' },
  { id: 'invoice', label: 'Invoice' },
  { id: 'notes', label: 'Notes' },
];

// ── Helper: authenticated fetch ────────────────────────────────────────────────

function authFetch(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token') || localStorage.getItem('aegis_token');
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  return (
    <span style={{
      background: STATUS_COLORS[status] || '#999',
      color: 'white',
      borderRadius: 4,
      padding: '3px 10px',
      fontSize: 12,
      fontWeight: 600,
    }}>
      {status.replace('_', ' ')}
    </span>
  );
}

function IntakeDisplay({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== '' && v !== undefined);
  if (entries.length === 0) return <p style={{ color: 'var(--muted)', fontSize: 13 }}>No intake data recorded.</p>;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
      {entries.map(([k, v]) => (
        <div key={k} style={{ borderLeft: '3px solid var(--border)', paddingLeft: 10 }}>
          <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>
            {k.replace(/_/g, ' ')}
          </div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>{String(v)}</div>
        </div>
      ))}
    </div>
  );
}

// ── Generate Document Modal ────────────────────────────────────────────────────

const DOC_TYPES = [
  'Cover Letter',
  'Demand Letter',
  'Affidavit',
  'Engagement Agreement',
  'Service Summary',
  'Progress Report',
  'Invoice Cover',
  'Other',
];

function GenerateDocModal({
  caseId,
  onClose,
  onGenerated,
}: {
  caseId: number;
  onClose: () => void;
  onGenerated: () => void;
}) {
  const [docType, setDocType] = useState('');
  const [instructions, setInstructions] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!docType) { setError('Select a document type.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await authFetch(`/api/documents/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_case_id: caseId,
          document_type: docType,
          custom_instructions: instructions || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      onGenerated();
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to generate document.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--surface)', borderRadius: 'var(--radius)',
        padding: 28, width: '100%', maxWidth: 480, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
      }}>
        <h3 style={{ marginBottom: 18, color: 'var(--navy)' }}>Generate Document</h3>
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Document Type *</label>
            <select value={docType} onChange={e => setDocType(e.target.value)} required>
              <option value="">— Select Type —</option>
              {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Custom Instructions (optional)</label>
            <textarea
              rows={3}
              value={instructions}
              onChange={e => setInstructions(e.target.value)}
              placeholder="Any specific details, tone, or content to include…"
            />
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Generating…' : 'Generate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Schedule Appointment Modal ─────────────────────────────────────────────────

const APPT_TYPES = ['consultation', 'signing', 'document_review', 'intake'];

function ScheduleModal({
  caseId,
  clientId,
  divisionSlug,
  onClose,
  onScheduled,
}: {
  caseId: number;
  clientId: number;
  divisionSlug: string;
  onClose: () => void;
  onScheduled: () => void;
}) {
  const [form, setForm] = useState({ appointment_type: 'consultation', scheduled_at: '', location: '', notes: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.scheduled_at) { setError('Date and time are required.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await authFetch(`/api/appointments/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          service_case_id: caseId,
          division_slug: divisionSlug,
          appointment_type: form.appointment_type,
          scheduled_at: form.scheduled_at,
          location: form.location || undefined,
          notes: form.notes || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      onScheduled();
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to schedule appointment.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--surface)', borderRadius: 'var(--radius)',
        padding: 28, width: '100%', maxWidth: 480, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
      }}>
        <h3 style={{ marginBottom: 18, color: 'var(--navy)' }}>Schedule Appointment</h3>
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Type *</label>
            <select value={form.appointment_type} onChange={e => setForm(f => ({ ...f, appointment_type: e.target.value }))}>
              {APPT_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Date & Time *</label>
            <input
              type="datetime-local"
              value={form.scheduled_at}
              onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))}
              required
            />
          </div>
          <div className="form-group">
            <label>Location</label>
            <input
              value={form.location}
              onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
              placeholder="Address or video link"
            />
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Any preparation notes…"
            />
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Scheduling…' : 'Schedule'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create Invoice Modal ───────────────────────────────────────────────────────

function CreateInvoiceModal({
  caseId,
  clientId,
  divisionSlug,
  onClose,
  onCreated,
}: {
  caseId: number;
  clientId: number;
  divisionSlug: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({ amount: '', due_date: '', description: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.amount) { setError('Amount is required.'); return; }
    const amt = parseFloat(form.amount);
    setLoading(true);
    setError('');
    try {
      const res = await authFetch(`/api/invoices/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          service_case_id: caseId,
          division_slug: divisionSlug,
          line_items: [{ description: form.description || 'Services rendered', quantity: 1, unit_price: amt, total: amt }],
          subtotal: amt,
          total: amt,
          due_date: form.due_date || undefined,
          status: 'draft',
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to create invoice.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div style={{
        background: 'var(--surface)', borderRadius: 'var(--radius)',
        padding: 28, width: '100%', maxWidth: 420, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
      }}>
        <h3 style={{ marginBottom: 18, color: 'var(--navy)' }}>Create Invoice</h3>
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Amount ($) *</label>
            <input
              type="number"
              step="0.01"
              value={form.amount}
              onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
              placeholder="0.00"
              required
            />
          </div>
          <div className="form-group">
            <label>Due Date</label>
            <input
              type="date"
              value={form.due_date}
              onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
            />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea
              rows={2}
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Services rendered…"
            />
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create Invoice'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

function ServiceCaseDetailInner() {
  const { division, caseId } = useParams<{ division: string; caseId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState(searchParams?.get('tab') || 'overview');
  const [caseData, setCaseData] = useState<ServiceCase | null>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [notes, setNotes] = useState('');
  const [notesSaved, setNotesSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  // Modal state
  const [showGenDoc, setShowGenDoc] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [showInvoice, setShowInvoice] = useState(false);

  const numericId = parseInt(caseId);

  const loadCase = useCallback(() => {
    return authFetch(`/api/service-cases/${numericId}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: ServiceCase) => {
        setCaseData(d);
        setNotes(d.notes || '');
      });
  }, [numericId]);

  const loadDocs = useCallback(() => {
    return authFetch(`/api/documents/?service_case_id=${numericId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setDocs)
      .catch(() => {});
  }, [numericId]);

  const loadAppointments = useCallback(() => {
    return authFetch(`/api/appointments/?service_case_id=${numericId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setAppointments)
      .catch(() => {});
  }, [numericId]);

  const loadInvoices = useCallback(() => {
    return authFetch(`/api/invoices/?service_case_id=${numericId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setInvoices)
      .catch(() => {});
  }, [numericId]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadCase(), loadDocs(), loadAppointments(), loadInvoices()])
      .catch(e => setError(e.message || 'Failed to load case.'))
      .finally(() => setLoading(false));
  }, [loadCase, loadDocs, loadAppointments, loadInvoices]);

  async function changeStatus(status: string) {
    if (!caseData) return;
    setSaving(true);
    try {
      const res = await authFetch(`/api/service-cases/${numericId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        const d = await res.json();
        setCaseData(d);
      }
    } finally {
      setSaving(false);
    }
  }

  async function saveNotes() {
    setSaving(true);
    setNotesSaved(false);
    try {
      const res = await authFetch(`/api/service-cases/${numericId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes }),
      });
      if (res.ok) setNotesSaved(true);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="main-layout">
        <Sidebar />
        <main className="main-content"><div className="spinner" /></main>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="main-layout">
        <Sidebar />
        <main className="main-content">
          <div className="alert-error">{error || 'Case not found.'}</div>
          <Link href={`/services/${division}`} className="btn btn-outline">
            Back to Division
          </Link>
        </main>
      </div>
    );
  }

  const divisionLabel = DIVISION_LABELS[caseData.division_slug || division] || division;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        {/* Page header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <Link href="/services" style={{ fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
                Services
              </Link>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>/</span>
              <Link href={`/services/${division}`} style={{ fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
                {divisionLabel}
              </Link>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>/</span>
              <code style={{ fontSize: 12 }}>{caseData.case_number}</code>
            </div>
            <h1 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              Case <code>{caseData.case_number}</code>
              <StatusBadge status={caseData.status} />
            </h1>
            <p>
              {caseData.client_name} &middot; Opened {new Date(caseData.created_at).toLocaleDateString()}
            </p>
          </div>
          <select
            value={caseData.status}
            onChange={e => changeStatus(e.target.value)}
            disabled={saving}
            style={{
              padding: '7px 12px', borderRadius: 'var(--radius)',
              border: '1px solid var(--border)', fontSize: 13,
            }}
          >
            {STATUSES.map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>

        {/* Tab navigation */}
        <div className="case-nav">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '8px 14px',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === t.id ? '2px solid var(--navy)' : '2px solid transparent',
                color: activeTab === t.id ? 'var(--navy)' : 'var(--muted)',
                marginBottom: -1,
              }}
            >
              {t.label}
              {t.id === 'documents' && docs.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.7 }}>({docs.length})</span>
              )}
              {t.id === 'appointments' && appointments.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.7 }}>({appointments.length})</span>
              )}
              {t.id === 'invoice' && invoices.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.7 }}>({invoices.length})</span>
              )}
            </button>
          ))}
        </div>

        {/* ── Overview tab ── */}
        {activeTab === 'overview' && (
          <>
            <div className="card">
              <h3>Client Information</h3>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Client</div>
                  <div style={{ fontWeight: 600, marginTop: 2 }}>
                    <Link href={`/clients/${caseData.client_id}`}>{caseData.client_name}</Link>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Division</div>
                  <div style={{ fontWeight: 600, marginTop: 2 }}>{divisionLabel}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</div>
                  <div style={{ marginTop: 4 }}><StatusBadge status={caseData.status} /></div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Opened</div>
                  <div style={{ fontWeight: 600, marginTop: 2 }}>{new Date(caseData.created_at).toLocaleDateString()}</div>
                </div>
              </div>
            </div>

            <div className="card">
              <h3>Intake Data</h3>
              <IntakeDisplay data={caseData.intake_data || {}} />
            </div>
          </>
        )}

        {/* ── Documents tab ── */}
        {activeTab === 'documents' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Generated Documents</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setShowGenDoc(true)}>
                + Generate Document
              </button>
            </div>
            {docs.length === 0 ? (
              <p className="empty">No documents generated yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map(d => (
                    <tr key={d.id}>
                      <td style={{ fontWeight: 500 }}>{d.title}</td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>{d.document_type}</td>
                      <td>
                        <span style={{
                          fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                          background: d.status === 'signed' ? '#d1fae5' : d.status === 'draft' ? '#f1f5f9' : '#fef3c7',
                          color: d.status === 'signed' ? '#065f46' : d.status === 'draft' ? '#475569' : '#92400e',
                        }}>{d.status}</span>
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {new Date(d.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <a
                          href={`/api/documents/${d.id}/download`}
                          className="btn btn-outline btn-sm"
                          target="_blank"
                          rel="noreferrer"
                        >
                          Download
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ── Appointments tab ── */}
        {activeTab === 'appointments' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Appointments</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setShowSchedule(true)}>
                + Schedule
              </button>
            </div>
            {appointments.length === 0 ? (
              <p className="empty">No appointments scheduled yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Date & Time</th>
                    <th>Location</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map(a => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 500, textTransform: 'capitalize' }}>{a.appointment_type?.replace('_', ' ')}</td>
                      <td style={{ fontSize: 12 }}>
                        {new Date(a.scheduled_at).toLocaleString()}
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>{a.location || '—'}</td>
                      <td>
                        <span style={{
                          background: a.status === 'completed' ? '#d1fae5' : a.status === 'cancelled' ? '#fee2e2' : '#dbeafe',
                          color: a.status === 'completed' ? '#065f46' : a.status === 'cancelled' ? '#991b1b' : '#1d4ed8',
                          borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
                        }}>
                          {a.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ── Invoice tab ── */}
        {activeTab === 'invoice' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Invoice</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setShowInvoice(true)}>
                + Create Invoice
              </button>
            </div>
            {invoices.length === 0 ? (
              <p className="empty">No invoice created yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Invoice #</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Due Date</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(inv => (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 600 }}><code>{inv.invoice_number}</code></td>
                      <td>${Number(inv.total).toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                      <td>
                        <span style={{
                          background: inv.status === 'paid' ? '#d1fae5' : inv.status === 'overdue' ? '#fee2e2' : '#fef3c7',
                          color: inv.status === 'paid' ? '#065f46' : inv.status === 'overdue' ? '#991b1b' : '#92400e',
                          borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600,
                        }}>
                          {inv.status}
                        </span>
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '—'}
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {new Date(inv.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* ── Notes tab ── */}
        {activeTab === 'notes' && (
          <div className="card">
            <h3>Internal Notes</h3>
            <textarea
              rows={10}
              value={notes}
              onChange={e => { setNotes(e.target.value); setNotesSaved(false); }}
              placeholder="Add case notes here (internal use only)…"
              style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6 }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
              <button
                className="btn btn-primary"
                onClick={saveNotes}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save Notes'}
              </button>
              {notesSaved && (
                <span style={{ fontSize: 12, color: 'var(--success)' }}>Saved.</span>
              )}
            </div>
          </div>
        )}

        {/* Modals */}
        {showGenDoc && (
          <GenerateDocModal
            caseId={numericId}
            onClose={() => setShowGenDoc(false)}
            onGenerated={loadDocs}
          />
        )}
        {showSchedule && (
          <ScheduleModal
            caseId={numericId}
            clientId={caseData.client_id}
            divisionSlug={caseData.division_slug}
            onClose={() => setShowSchedule(false)}
            onScheduled={loadAppointments}
          />
        )}
        {showInvoice && (
          <CreateInvoiceModal
            caseId={numericId}
            clientId={caseData.client_id}
            divisionSlug={caseData.division_slug}
            onClose={() => setShowInvoice(false)}
            onCreated={loadInvoices}
          />
        )}
      </main>
    </div>
  );
}

export default function ServiceCaseDetailPage() {
  return (
    <Suspense fallback={
      <div className="main-layout">
        <main style={{ padding: 40 }}><div className="spinner" /></main>
      </div>
    }>
      <ServiceCaseDetailInner />
    </Suspense>
  );
}
