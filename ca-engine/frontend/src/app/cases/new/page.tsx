'use client';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { createCase, listClients } from '@/lib/api';

const DIVISIONS = [
  { value: 'notary', label: 'Notary Services' },
  { value: 'credit', label: 'Credit Services' },
  { value: 'reentry', label: 'Community Reentry' },
  { value: 'document_prep', label: 'Document Preparation' },
  { value: 'asset_recovery', label: 'Asset Recovery' },
  { value: 'business', label: 'Business Formation' },
];

const INTAKE_FIELDS: Record<string, { key: string; label: string; type?: string; placeholder?: string }[]> = {
  notary: [
    { key: 'document_type', label: 'Document Type', placeholder: 'e.g., Deed of Trust, Affidavit' },
    { key: 'num_acts', label: 'Number of Notarial Acts', type: 'number', placeholder: '1' },
    { key: 'location', label: 'Location / Address of Service' },
    { key: 'travel_fee', label: 'Travel Fee ($)', type: 'number', placeholder: '0' },
    { key: 'service_fee', label: 'Signing Agent Service Fee ($)', type: 'number', placeholder: '0' },
  ],
  credit: [
    { key: 'credit_goal', label: 'Primary Credit Goal', placeholder: 'e.g., Mortgage qualification, Auto loan' },
    { key: 'current_score', label: 'Current Credit Score (approx.)', type: 'number' },
    { key: 'negative_items', label: 'Known Negative Items', placeholder: 'e.g., Collections, Late payments, Charge-offs' },
    { key: 'bureaus_to_dispute', label: 'Bureaus to Dispute (Equifax, Experian, TransUnion)' },
    { key: 'authorized_user', label: 'Authorized User / Identity Verification', placeholder: 'Name on account' },
  ],
  reentry: [
    { key: 'offense_description', label: 'Offense Description (general)', placeholder: 'e.g., Non-violent drug offense' },
    { key: 'release_date', label: 'Release Date', type: 'date' },
    { key: 'supervision_status', label: 'Current Supervision Status', placeholder: 'e.g., Probation, Parole, Discharged' },
    { key: 'employment_goal', label: 'Employment / Housing Goal' },
    { key: 'rehab_programs', label: 'Rehabilitation Programs Completed', placeholder: 'e.g., GED, Vocational training, AA' },
    { key: 'documents_needed', label: 'Documents Needed', placeholder: 'e.g., Explanation letter, Pardon support packet' },
  ],
  document_prep: [
    { key: 'document_type', label: 'Document Type Requested' },
    { key: 'purpose', label: 'Purpose / Intended Use' },
    { key: 'recipient', label: 'Recipient / Organization' },
    { key: 'deadline', label: 'Deadline', type: 'date' },
    { key: 'special_instructions', label: 'Special Instructions or Details' },
  ],
  asset_recovery: [
    { key: 'asset_type', label: 'Asset Type', placeholder: 'e.g., Surplus funds, Unclaimed property, Overage' },
    { key: 'property_address', label: 'Property Address (if applicable)' },
    { key: 'county', label: 'County / Jurisdiction' },
    { key: 'case_number', label: 'Foreclosure/Court Case Number (if known)' },
    { key: 'estimated_amount', label: 'Estimated Amount ($)', type: 'number' },
  ],
  business: [
    { key: 'business_name', label: 'Proposed Business Name' },
    { key: 'business_type', label: 'Entity Type', placeholder: 'LLC, Sole Proprietor, Corp' },
    { key: 'business_description', label: 'Business Description / Services' },
    { key: 'target_market', label: 'Target Market' },
    { key: 'ein_needed', label: 'EIN / Tax ID Needed?', placeholder: 'Yes / No' },
    { key: 'registered_agent', label: 'Registered Agent Name (if known)' },
  ],
};

interface Client { id: number; first_name: string; last_name: string; }

function NewCaseForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedClientId = searchParams.get('client_id');

  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState({
    client_id: preselectedClientId || '',
    division: 'credit',
    notes: '',
    assigned_to: '',
  });
  const [intakeData, setIntakeData] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listClients().then(setClients);
  }, []);

  function setField(key: string, val: string) { setForm((f) => ({ ...f, [key]: val })); }
  function setIntake(key: string, val: string) { setIntakeData((d) => ({ ...d, [key]: val })); }

  const intakeFields = INTAKE_FIELDS[form.division] || [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!form.client_id) { setError('Please select a client.'); return; }
    setLoading(true);
    try {
      const caseData = await createCase({
        client_id: parseInt(form.client_id),
        division: form.division,
        intake_data: intakeData,
        notes: form.notes,
        assigned_to: form.assigned_to,
      });
      router.push(`/cases/${caseData.id}`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = e.response?.data?.detail;
      setError(
        typeof detail === 'string' ? detail
        : detail ? JSON.stringify(detail)
        : e.message || 'Network error — check backend is running on port 8001.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>New Case</h1>
          <p>Complete intake to open a new case — AI analysis and documents generate automatically</p>
        </div>

        <div className="disclosure-banner">
          All services are administrative document preparation only. Cruel & Associates is not a law firm.
        </div>

        <form onSubmit={handleSubmit} style={{ maxWidth: 720 }}>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Case Setup</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Client *</label>
                <select value={form.client_id} onChange={(e) => setField('client_id', e.target.value)} required>
                  <option value="">— Select Client —</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Division *</label>
                <select value={form.division} onChange={(e) => { setField('division', e.target.value); setIntakeData({}); }}>
                  {DIVISIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Assigned To</label>
              <input
                value={form.assigned_to}
                onChange={(e) => setField('assigned_to', e.target.value)}
                placeholder="Staff member name (optional)"
              />
            </div>
          </div>

          {intakeFields.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ color: 'var(--navy)', marginBottom: 4 }}>
                {DIVISIONS.find((d) => d.value === form.division)?.label} — Intake Information
              </h3>
              <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
                This information is used for AI analysis and automatic document generation.
              </p>
              {intakeFields.map((field) => (
                <div className="form-group" key={field.key}>
                  <label>{field.label}</label>
                  <input
                    type={field.type || 'text'}
                    value={intakeData[field.key] || ''}
                    onChange={(e) => setIntake(field.key, e.target.value)}
                    placeholder={field.placeholder}
                  />
                </div>
              ))}
            </div>
          )}

          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 12 }}>Internal Notes</h3>
            <div className="form-group">
              <textarea
                rows={3}
                value={form.notes}
                onChange={(e) => setField('notes', e.target.value)}
                placeholder="Internal case notes (not included in client documents)…"
              />
            </div>
          </div>

          <div style={{
            background: '#f0f9ff', border: '1px solid #0ea5e9', borderRadius: 8,
            padding: '12px 16px', marginBottom: 16, fontSize: 13, color: '#0369a1',
          }}>
            After submitting, the system will automatically: run AI case analysis, generate default
            service agreement, and send a confirmation email to the client.
          </div>

          {error && <p className="error-msg" style={{ marginBottom: 12 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating Case & Running Automation…' : 'Create Case'}
            </button>
            <button type="button" className="btn btn-outline" onClick={() => router.back()}>Cancel</button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default function NewCasePage() {
  return (
    <Suspense fallback={<div className="main-layout"><div style={{ padding: 40 }}><div className="spinner" /></div></div>}>
      <NewCaseForm />
    </Suspense>
  );
}
