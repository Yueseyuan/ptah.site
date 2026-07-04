'use client';
import { useEffect, useState, useCallback, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import api, { getToken } from '@/lib/api';

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

interface Referral {
  id: number;
  client_id: number;
  service_case_id: number | null;
  attorney_name: string | null;
  attorney_firm: string | null;
  attorney_email: string | null;
  attorney_phone: string | null;
  practice_area: string | null;
  reason: string | null;
  status: string;
  referral_letter_path: string | null;
  notes: string | null;
  referred_at: string | null;
}

interface NotaryLog {
  id: number;
  client_id: number;
  service_case_id: number | null;
  journal_number: string | null;
  document_type: string | null;
  signer_name: string | null;
  signer_id_type: string | null;
  num_signers: number | null;
  notarized_at: string | null;
  location: string | null;
  fee_charged: number | null;
  notes: string | null;
  created_at: string | null;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const DIVISION_LABELS: Record<string, string> = {
  notary: 'Mobile Notary',
  credit: 'Credit Restoration',
  criminal: 'Criminal Record Relief',
  document: 'Document Preparation',
  judgment: 'Judgment & Asset Recovery',
  consulting: 'Business Consulting',
  overages: 'Tax Overage Recovery',
};

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6',
  active: '#10b981',
  on_hold: '#f59e0b',
  closed: '#6b7280',
};

const STATUSES = ['intake', 'active', 'on_hold', 'closed'];

const BASE_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'documents', label: 'Documents' },
  { id: 'appointments', label: 'Appointments' },
  { id: 'invoice', label: 'Invoice' },
  { id: 'notes', label: 'Notes' },
];

const DIVISION_EXTRA_TABS: Record<string, { id: string; label: string }[]> = {
  criminal: [{ id: 'referrals', label: 'Referrals' }],
  notary:   [{ id: 'journal',   label: 'Notary Journal' }],
  judgment: [{ id: 'referrals', label: 'Referrals' }],
  overages: [{ id: 'workflow',  label: 'Recovery Workflow' }],
};

// ── Helper: authenticated fetch ────────────────────────────────────────────────

function authFetch(url: string, options: RequestInit = {}) {
  const token = getToken();
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

// ── Judgment Workflow Card ────────────────────────────────────────────────────

const WORKFLOW_STEPS = [
  { n: 1, label: 'Client Intake',           desc: 'Collect judgment docs, court info, debtor data, prior efforts' },
  { n: 2, label: 'Judgment Verification',   desc: 'Confirm validity, remaining balance, renewal, enforceability' },
  { n: 3, label: 'Collectability Assessment', desc: 'Evaluate assets, assign collectability score (1–100)' },
  { n: 4, label: 'Asset Investigation',     desc: 'Search public records: property, UCC, corporate, bankruptcy' },
  { n: 5, label: 'Recovery Strategy',       desc: 'Demand letters, settlement talks, attorney coordination' },
  { n: 6, label: 'Case Management',         desc: 'Track communications, deadlines, costs, recoveries' },
  { n: 7, label: 'Case Closure',            desc: 'Document recovery, fees, satisfaction, final report' },
];

function JudgmentWorkflowCard({
  caseId,
  intakeData,
  onSaved,
}: {
  caseId: number;
  intakeData: Record<string, unknown>;
  onSaved: () => void;
}) {
  const currentStep = Number(intakeData.workflow_step) || 1;
  const collectabilityScore = intakeData.collectability_score != null ? String(intakeData.collectability_score) : '';

  const [pendingStep, setPendingStep] = useState(currentStep);
  const [score, setScore] = useState(collectabilityScore);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setPendingStep(Number(intakeData.workflow_step) || 1);
    setScore(intakeData.collectability_score != null ? String(intakeData.collectability_score) : '');
  }, [intakeData]);

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      await api.put(`/api/service-cases/${caseId}`, {
        intake_data: { ...intakeData, workflow_step: pendingStep, collectability_score: score ? Number(score) : null },
      });
      setSaved(true); onSaved();
    } finally {
      setSaving(false);
    }
  }

  const scoreNum = parseFloat(score);
  const scoreColor = !score ? '#6b7280' : scoreNum >= 70 ? '#10b981' : scoreNum >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Recovery Workflow</h3>

      {/* Step progress */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, overflowX: 'auto' }}>
        {WORKFLOW_STEPS.map((step, i) => {
          const isDone = step.n < pendingStep;
          const isActive = step.n === pendingStep;
          return (
            <button
              key={step.n}
              onClick={() => { setPendingStep(step.n); setSaved(false); }}
              title={step.desc}
              style={{
                flex: '1 1 0',
                minWidth: 80,
                padding: '10px 6px',
                border: 'none',
                borderBottom: isActive ? '3px solid var(--navy)' : isDone ? '3px solid #10b981' : '3px solid var(--border)',
                background: isActive ? 'var(--navy-light, #eff6ff)' : 'transparent',
                cursor: 'pointer',
                textAlign: 'center',
                position: 'relative',
              }}
            >
              <div style={{
                width: 28, height: 28, borderRadius: '50%', margin: '0 auto 6px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700,
                background: isActive ? 'var(--navy)' : isDone ? '#10b981' : 'var(--border)',
                color: isActive || isDone ? 'white' : 'var(--muted)',
              }}>
                {isDone ? '✓' : step.n}
              </div>
              <div style={{ fontSize: 10, fontWeight: isActive ? 700 : 400, color: isActive ? 'var(--navy)' : 'var(--muted)', lineHeight: 1.2 }}>
                {step.label}
              </div>
            </button>
          );
        })}
      </div>

      {/* Active step description */}
      <div style={{ background: 'var(--surface-alt, #f8fafc)', borderRadius: 'var(--radius)', padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
        <strong>Step {pendingStep}: {WORKFLOW_STEPS[pendingStep - 1]?.label}</strong>
        <div style={{ color: 'var(--muted)', marginTop: 4 }}>{WORKFLOW_STEPS[pendingStep - 1]?.desc}</div>
      </div>

      {/* Collectability score */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>
            Collectability Score (1–100)
          </label>
          <input
            type="number"
            min="1"
            max="100"
            value={score}
            onChange={e => { setScore(e.target.value); setSaved(false); }}
            placeholder="—"
            style={{ width: 80, padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 14, fontWeight: 700, color: scoreColor, fontVariantNumeric: 'tabular-nums' }}
          />
        </div>
        {score && (
          <div style={{ fontSize: 12, color: scoreColor, fontWeight: 600, paddingTop: 18 }}>
            {scoreNum >= 70 ? 'High collectability' : scoreNum >= 40 ? 'Moderate collectability' : 'Low collectability'}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save Workflow'}
        </button>
        {saved && <span style={{ fontSize: 12, color: 'var(--success)' }}>Saved.</span>}
      </div>
    </div>
  );
}

// ── Overages Workflow Card ────────────────────────────────────────────────────

const OVERAGES_STEPS = [
  { n: 1,  label: 'Lead Source',        desc: 'County spreadsheet review — identify potential surplus case' },
  { n: 2,  label: 'Case Verification',  desc: 'Confirm surplus exists and is still unclaimed with the county' },
  { n: 3,  label: 'Owner Research',     desc: 'Pull property records, confirm former owner and parcel/folio' },
  { n: 4,  label: 'Skip Trace',         desc: 'Locate current contact information for the former owner' },
  { n: 5,  label: 'Outreach',           desc: 'Phone, text, and email contact with the former owner' },
  { n: 6,  label: 'Agreement Signed',   desc: 'Contingency agreement and non-lawyer disclosure executed' },
  { n: 7,  label: 'Authorization',      desc: 'Authorization to act on behalf of owner signed' },
  { n: 8,  label: 'Claim Assistance',   desc: 'Prepare and submit surplus fund claim to county' },
  { n: 9,  label: 'Recovery',           desc: 'Funds received from county and disbursement confirmed' },
  { n: 10, label: 'Fee Collected',      desc: 'Company contingency fee disbursed, case closed' },
];

const DEFAULT_FEE_PCT = 35;

function OveragesWorkflowCard({
  caseId,
  intakeData,
  onSaved,
}: {
  caseId: number;
  intakeData: Record<string, unknown>;
  onSaved: () => void;
}) {
  const currentStep = Number(intakeData.workflow_step) || 1;
  const [pendingStep, setPendingStep] = useState(currentStep);
  const [feePct, setFeePct] = useState(
    intakeData.fee_percentage != null ? String(intakeData.fee_percentage) : String(DEFAULT_FEE_PCT)
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setPendingStep(Number(intakeData.workflow_step) || 1);
    setFeePct(intakeData.fee_percentage != null ? String(intakeData.fee_percentage) : String(DEFAULT_FEE_PCT));
  }, [intakeData]);

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      await api.put(`/api/service-cases/${caseId}`, {
        intake_data: { ...intakeData, workflow_step: pendingStep, fee_percentage: feePct ? Number(feePct) : DEFAULT_FEE_PCT },
      });
      setSaved(true); onSaved();
    } finally {
      setSaving(false);
    }
  }

  const surplus = parseFloat(String(intakeData.estimated_surplus || '0')) || 0;
  const pct = parseFloat(feePct) || DEFAULT_FEE_PCT;
  const estimatedFee = surplus * (pct / 100);
  const netToClient = surplus - estimatedFee;

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>10-Step Recovery Workflow</h3>

      {/* Step progress */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, overflowX: 'auto' }}>
        {OVERAGES_STEPS.map(step => {
          const isDone = step.n < pendingStep;
          const isActive = step.n === pendingStep;
          return (
            <button
              key={step.n}
              onClick={() => { setPendingStep(step.n); setSaved(false); }}
              title={step.desc}
              style={{
                flex: '1 1 0',
                minWidth: 72,
                padding: '10px 4px',
                border: 'none',
                borderBottom: isActive ? '3px solid var(--navy)' : isDone ? '3px solid #10b981' : '3px solid var(--border)',
                background: isActive ? 'var(--navy-light, #eff6ff)' : 'transparent',
                cursor: 'pointer',
                textAlign: 'center',
              }}
            >
              <div style={{
                width: 26, height: 26, borderRadius: '50%', margin: '0 auto 5px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700,
                background: isActive ? 'var(--navy)' : isDone ? '#10b981' : 'var(--border)',
                color: isActive || isDone ? 'white' : 'var(--muted)',
              }}>
                {isDone ? '✓' : step.n}
              </div>
              <div style={{ fontSize: 9, fontWeight: isActive ? 700 : 400, color: isActive ? 'var(--navy)' : 'var(--muted)', lineHeight: 1.2 }}>
                {step.label}
              </div>
            </button>
          );
        })}
      </div>

      {/* Active step description */}
      <div style={{ background: 'var(--surface-alt, #f8fafc)', borderRadius: 'var(--radius)', padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
        <strong>Step {pendingStep}: {OVERAGES_STEPS[pendingStep - 1]?.label}</strong>
        <div style={{ color: 'var(--muted)', marginTop: 4 }}>{OVERAGES_STEPS[pendingStep - 1]?.desc}</div>
      </div>

      {/* Fee calculator */}
      <div style={{ background: 'var(--surface-alt, #f8fafc)', borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
          Fee Calculator
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-end' }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
              Estimated Surplus
            </label>
            <div style={{ fontWeight: 700, fontSize: 18, fontVariantNumeric: 'tabular-nums' }}>
              ${surplus > 0 ? surplus.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '—'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)' }}>from intake data</div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--muted)', display: 'block', marginBottom: 4 }}>
              Fee % (default 35%)
            </label>
            <input
              type="number"
              min="1"
              max="50"
              step="0.5"
              value={feePct}
              onChange={e => { setFeePct(e.target.value); setSaved(false); }}
              style={{ width: 72, padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 14, fontWeight: 600 }}
            />
          </div>
          {surplus > 0 && (
            <>
              <div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Est. Company Fee</div>
                <div style={{ fontWeight: 700, fontSize: 18, color: '#1d4ed8', fontVariantNumeric: 'tabular-nums' }}>
                  ${estimatedFee.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>Net to Client</div>
                <div style={{ fontWeight: 700, fontSize: 18, color: '#10b981', fontVariantNumeric: 'tabular-nums' }}>
                  ${netToClient.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save Workflow'}
        </button>
        {saved && <span style={{ fontSize: 12, color: 'var(--success)' }}>Saved.</span>}
      </div>
    </div>
  );
}

// ── Create Notary Log Modal ───────────────────────────────────────────────────

function CreateNotaryLogModal({
  caseId,
  clientId,
  onClose,
  onCreated,
}: {
  caseId: number;
  clientId: number;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    document_type: '',
    signer_name: '',
    signer_id_type: 'drivers_license',
    signer_id_number: '',
    num_signers: '1',
    notarized_at: '',
    location: '',
    fee_charged: '',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.document_type.trim()) { setError('Document type is required.'); return; }
    if (!form.signer_name.trim()) { setError('Signer name is required.'); return; }
    if (!form.notarized_at) { setError('Date & time of notarization is required.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await authFetch('/api/notary/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          service_case_id: caseId,
          document_type: form.document_type,
          signer_name: form.signer_name,
          signer_id_type: form.signer_id_type,
          signer_id_number: form.signer_id_number || undefined,
          num_signers: parseInt(form.num_signers) || 1,
          notarized_at: form.notarized_at,
          location: form.location || undefined,
          fee_charged: form.fee_charged ? parseFloat(form.fee_charged) : undefined,
          notes: form.notes || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to create journal entry.');
    } finally {
      setLoading(false);
    }
  }

  const f = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm(prev => ({ ...prev, [k]: e.target.value }));

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: 28, width: '100%', maxWidth: 520, boxShadow: '0 8px 32px rgba(0,0,0,0.15)', maxHeight: '90vh', overflowY: 'auto' }}>
        <h3 style={{ marginBottom: 18, color: 'var(--navy)' }}>Add Notary Journal Entry</h3>
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Document Type *</label>
            <input value={form.document_type} onChange={f('document_type')} placeholder="e.g., Deed, Affidavit, Power of Attorney" required />
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Signer Name *</label>
              <input value={form.signer_name} onChange={f('signer_name')} placeholder="Full legal name" required />
            </div>
            <div className="form-group">
              <label>ID Type *</label>
              <select value={form.signer_id_type} onChange={f('signer_id_type')}>
                <option value="drivers_license">Driver&apos;s License</option>
                <option value="passport">Passport</option>
                <option value="state_id">State ID</option>
              </select>
            </div>
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>ID Number</label>
              <input value={form.signer_id_number} onChange={f('signer_id_number')} placeholder="Optional" />
            </div>
            <div className="form-group">
              <label>Number of Signers</label>
              <input type="number" min="1" value={form.num_signers} onChange={f('num_signers')} />
            </div>
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Date &amp; Time *</label>
              <input type="datetime-local" value={form.notarized_at} onChange={f('notarized_at')} required />
            </div>
            <div className="form-group">
              <label>Fee Charged ($)</label>
              <input type="number" step="0.01" value={form.fee_charged} onChange={f('fee_charged')} placeholder="0.00" />
            </div>
          </div>
          <div className="form-group">
            <label>Location</label>
            <input value={form.location} onChange={f('location')} placeholder="Address or 'Remote'" />
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea rows={2} value={form.notes} onChange={f('notes')} placeholder="Any additional journal notes…" />
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving…' : 'Add Entry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create Referral Modal ─────────────────────────────────────────────────────

const PRACTICE_AREAS = [
  'Criminal Defense',
  'Expungement / Record Sealing',
  'Post-Conviction Relief',
  'Immigration',
  'Employment Law',
  'Civil Rights',
  'Other',
];

const REFERRAL_STATUSES = ['pending', 'accepted', 'declined', 'completed'];

function CreateReferralModal({
  caseId,
  clientId,
  onClose,
  onCreated,
}: {
  caseId: number;
  clientId: number;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    attorney_name: '',
    attorney_firm: '',
    attorney_email: '',
    attorney_phone: '',
    practice_area: 'Criminal Defense',
    reason: '',
    notes: '',
    status: 'pending',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.reason.trim()) { setError('Reason for referral is required.'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await authFetch('/api/referrals/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          service_case_id: caseId,
          attorney_name: form.attorney_name || undefined,
          attorney_firm: form.attorney_firm || undefined,
          attorney_email: form.attorney_email || undefined,
          attorney_phone: form.attorney_phone || undefined,
          practice_area: form.practice_area || undefined,
          reason: form.reason,
          notes: form.notes || undefined,
          status: form.status,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      onCreated();
      onClose();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to create referral.');
    } finally {
      setLoading(false);
    }
  }

  const f = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }));

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', padding: 28, width: '100%', maxWidth: 540, boxShadow: '0 8px 32px rgba(0,0,0,0.15)', maxHeight: '90vh', overflowY: 'auto' }}>
        <h3 style={{ marginBottom: 18, color: 'var(--navy)' }}>Create Attorney Referral</h3>
        <form onSubmit={submit}>
          <div className="grid-2">
            <div className="form-group">
              <label>Attorney Name</label>
              <input value={form.attorney_name} onChange={f('attorney_name')} placeholder="Full name" />
            </div>
            <div className="form-group">
              <label>Firm</label>
              <input value={form.attorney_firm} onChange={f('attorney_firm')} placeholder="Law firm name" />
            </div>
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Attorney Email</label>
              <input type="email" value={form.attorney_email} onChange={f('attorney_email')} placeholder="attorney@firm.com" />
            </div>
            <div className="form-group">
              <label>Attorney Phone</label>
              <input type="tel" value={form.attorney_phone} onChange={f('attorney_phone')} placeholder="(555) 000-0000" />
            </div>
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Practice Area</label>
              <select value={form.practice_area} onChange={f('practice_area')}>
                {PRACTICE_AREAS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Status</label>
              <select value={form.status} onChange={f('status')}>
                {REFERRAL_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Reason for Referral *</label>
            <textarea rows={3} value={form.reason} onChange={f('reason')} placeholder="Describe why this client needs an attorney and what the attorney should know…" required />
          </div>
          <div className="form-group">
            <label>Internal Notes</label>
            <textarea rows={2} value={form.notes} onChange={f('notes')} placeholder="Any additional internal notes…" />
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create Referral'}
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
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [notaryLogs, setNotaryLogs] = useState<NotaryLog[]>([]);
  const [notes, setNotes] = useState('');
  const [notesSaved, setNotesSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [letterLoading, setLetterLoading] = useState<number | null>(null);
  const [letterMsg, setLetterMsg] = useState('');
  const [aiActionLoading, setAiActionLoading] = useState(false);
  const [aiActionMsg, setAiActionMsg] = useState('');

  // Modal state
  const [showGenDoc, setShowGenDoc] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [showInvoice, setShowInvoice] = useState(false);
  const [showCreateReferral, setShowCreateReferral] = useState(false);
  const [showCreateNotaryLog, setShowCreateNotaryLog] = useState(false);

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

  const loadReferrals = useCallback(() => {
    return authFetch(`/api/referrals/?service_case_id=${numericId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setReferrals)
      .catch(() => {});
  }, [numericId]);

  const loadNotaryLogs = useCallback(() => {
    return authFetch(`/api/notary/logs?service_case_id=${numericId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setNotaryLogs)
      .catch(() => {});
  }, [numericId]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadCase(), loadDocs(), loadAppointments(), loadInvoices(), loadReferrals(), loadNotaryLogs()])
      .catch(e => setError(e.message || 'Failed to load case.'))
      .finally(() => setLoading(false));
  }, [loadCase, loadDocs, loadAppointments, loadInvoices, loadReferrals, loadNotaryLogs]);

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

  async function generateLetter(referralId: number) {
    setLetterLoading(referralId);
    setLetterMsg('');
    try {
      const res = await authFetch(`/api/referrals/${referralId}/generate-letter`, { method: 'POST' });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      setLetterMsg(`Letter generated${body.ai_generated ? ' (AI)' : ''}: ${body.title || 'Referral Letter'}`);
      loadDocs();
    } catch (err: unknown) {
      setLetterMsg(`Error: ${(err as Error).message}`);
    } finally {
      setLetterLoading(null);
    }
  }

  async function runAiAction(endpoint: string, label: string) {
    setAiActionLoading(true);
    setAiActionMsg('');
    try {
      const res = await authFetch(endpoint, { method: 'POST' });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      setAiActionMsg(`${label} generated${body.ai_generated ? ' (AI)' : ''}. View it in the Documents tab.`);
      loadDocs();
    } catch (err: unknown) {
      setAiActionMsg(`Error: ${(err as Error).message}`);
    } finally {
      setAiActionLoading(false);
    }
  }

  const tabs = [
    ...BASE_TABS.slice(0, 4),
    ...(DIVISION_EXTRA_TABS[division] || []),
    BASE_TABS[4], // Notes always last
  ];

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
          {tabs.map(t => (
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
              {t.id === 'referrals' && referrals.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.7 }}>({referrals.length})</span>
              )}
              {t.id === 'journal' && notaryLogs.length > 0 && (
                <span style={{ marginLeft: 4, fontSize: 10, opacity: 0.7 }}>({notaryLogs.length})</span>
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

            {/* Judgment 7-step workflow tracker */}
            {division === 'judgment' && (
              <JudgmentWorkflowCard
                caseId={numericId}
                intakeData={caseData.intake_data || {}}
                onSaved={loadCase}
              />
            )}

            {/* Overages fee calculator (overview summary) */}
            {division === 'overages' && (() => {
              const surplus = parseFloat(String(caseData.intake_data?.estimated_surplus || '0')) || 0;
              const feePct = parseFloat(String(caseData.intake_data?.fee_percentage || '35')) || 35;
              return surplus > 0 ? (
                <div className="card">
                  <h3>Surplus Summary</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24 }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estimated Surplus</div>
                      <div style={{ fontWeight: 700, fontSize: 22, marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>
                        ${surplus.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Est. Fee ({feePct}%)</div>
                      <div style={{ fontWeight: 700, fontSize: 22, marginTop: 4, color: '#1d4ed8', fontVariantNumeric: 'tabular-nums' }}>
                        ${(surplus * feePct / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Net to Client</div>
                      <div style={{ fontWeight: 700, fontSize: 22, marginTop: 4, color: '#10b981', fontVariantNumeric: 'tabular-nums' }}>
                        ${(surplus * (1 - feePct / 100)).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div style={{ alignSelf: 'center' }}>
                      <button className="btn btn-outline btn-sm" onClick={() => setActiveTab('workflow')}>
                        Open Workflow
                      </button>
                    </div>
                  </div>
                </div>
              ) : null;
            })()}

            {/* Division-specific AI quick actions */}
            {(division === 'judgment' || division === 'consulting' || division === 'overages') && (
              <div className="card">
                <h3>AI Quick Actions</h3>
                {aiActionMsg && (
                  <div style={{
                    marginBottom: 12, padding: '10px 14px', borderRadius: 'var(--radius)',
                    background: aiActionMsg.startsWith('Error') ? '#fee2e2' : '#d1fae5',
                    color: aiActionMsg.startsWith('Error') ? '#991b1b' : '#065f46',
                    fontSize: 13,
                  }}>
                    {aiActionMsg}
                    <button onClick={() => setAiActionMsg('')} style={{ marginLeft: 10, background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, opacity: 0.7 }}>✕</button>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {division === 'judgment' && (
                    <button
                      className="btn btn-primary"
                      disabled={aiActionLoading}
                      onClick={() => runAiAction(`/api/judgment/${numericId}/recovery-plan`, 'Recovery Plan')}
                    >
                      {aiActionLoading ? 'Generating…' : '🤖 Generate Recovery Plan'}
                    </button>
                  )}
                  {division === 'consulting' && (
                    <button
                      className="btn btn-primary"
                      disabled={aiActionLoading}
                      onClick={() => runAiAction(`/api/consulting/${numericId}/advise`, 'Business Advisory')}
                    >
                      {aiActionLoading ? 'Generating…' : '🤖 Generate Business Advisory'}
                    </button>
                  )}
                  {division === 'overages' && (
                    <button
                      className="btn btn-primary"
                      disabled={aiActionLoading}
                      onClick={() => runAiAction(`/api/overages/${numericId}/score-lead`, 'Lead Score')}
                    >
                      {aiActionLoading ? 'Scoring…' : '🤖 Score This Lead'}
                    </button>
                  )}
                  <button
                    className="btn btn-outline"
                    onClick={() => { setActiveTab('documents'); }}
                  >
                    View Documents
                  </button>
                </div>
                <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 10, marginBottom: 0 }}>
                  AI-generated documents are saved to the Documents tab automatically.
                </p>
              </div>
            )}
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

        {/* ── Overages Recovery Workflow tab ── */}
        {activeTab === 'workflow' && (
          <OveragesWorkflowCard
            caseId={numericId}
            intakeData={caseData.intake_data || {}}
            onSaved={loadCase}
          />
        )}

        {/* ── Referrals tab ── */}
        {activeTab === 'referrals' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Attorney Referrals</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setShowCreateReferral(true)}>
                + Add Referral
              </button>
            </div>

            {letterMsg && (
              <div style={{
                marginBottom: 12, padding: '10px 14px', borderRadius: 'var(--radius)',
                background: letterMsg.startsWith('Error') ? '#fee2e2' : '#d1fae5',
                color: letterMsg.startsWith('Error') ? '#991b1b' : '#065f46',
                fontSize: 13,
              }}>
                {letterMsg}
                <button onClick={() => setLetterMsg('')} style={{ marginLeft: 10, background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, opacity: 0.7 }}>✕</button>
              </div>
            )}

            {referrals.length === 0 ? (
              <p className="empty">No attorney referrals yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {referrals.map(ref => (
                  <div key={ref.id} style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>
                          {ref.attorney_name || 'Attorney TBD'}
                          {ref.attorney_firm && <span style={{ color: 'var(--muted)', fontWeight: 400, fontSize: 13 }}> — {ref.attorney_firm}</span>}
                        </div>
                        {ref.practice_area && (
                          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{ref.practice_area}</div>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span style={{
                          fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
                          background: ref.status === 'accepted' ? '#d1fae5' : ref.status === 'declined' ? '#fee2e2' : ref.status === 'completed' ? '#dbeafe' : '#fef3c7',
                          color: ref.status === 'accepted' ? '#065f46' : ref.status === 'declined' ? '#991b1b' : ref.status === 'completed' ? '#1d4ed8' : '#92400e',
                        }}>
                          {ref.status}
                        </span>
                      </div>
                    </div>

                    {ref.reason && (
                      <div style={{ fontSize: 13, color: 'var(--text)', marginBottom: 10, lineHeight: 1.5 }}>
                        <span style={{ color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Reason: </span>
                        {ref.reason}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
                      {ref.attorney_email && <span>✉ {ref.attorney_email}</span>}
                      {ref.attorney_phone && <span>📞 {ref.attorney_phone}</span>}
                      {ref.referred_at && <span>Added {new Date(ref.referred_at).toLocaleDateString()}</span>}
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => generateLetter(ref.id)}
                        disabled={letterLoading === ref.id}
                      >
                        {letterLoading === ref.id ? 'Generating…' : '📄 Generate Letter'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Notary Journal tab ── */}
        {activeTab === 'journal' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Notary Journal</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setShowCreateNotaryLog(true)}>
                + Add Entry
              </button>
            </div>
            {notaryLogs.length === 0 ? (
              <p className="empty">No journal entries for this case yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Journal #</th>
                    <th>Document Type</th>
                    <th>Signer</th>
                    <th>Date &amp; Time</th>
                    <th>Location</th>
                    <th>Signers</th>
                    <th>Fee</th>
                  </tr>
                </thead>
                <tbody>
                  {notaryLogs.map(log => (
                    <tr key={log.id}>
                      <td><code style={{ fontSize: 11 }}>{log.journal_number || '—'}</code></td>
                      <td style={{ fontWeight: 500 }}>{log.document_type}</td>
                      <td>{log.signer_name}</td>
                      <td style={{ fontSize: 12, color: 'var(--muted)' }}>
                        {log.notarized_at ? new Date(log.notarized_at).toLocaleString() : '—'}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--muted)' }}>{log.location || '—'}</td>
                      <td style={{ textAlign: 'center' }}>{log.num_signers ?? 1}</td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                        {log.fee_charged != null ? `$${Number(log.fee_charged).toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
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
        {showCreateReferral && (
          <CreateReferralModal
            caseId={numericId}
            clientId={caseData.client_id}
            onClose={() => setShowCreateReferral(false)}
            onCreated={loadReferrals}
          />
        )}
        {showCreateNotaryLog && (
          <CreateNotaryLogModal
            caseId={numericId}
            clientId={caseData.client_id}
            onClose={() => setShowCreateNotaryLog(false)}
            onCreated={loadNotaryLogs}
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
