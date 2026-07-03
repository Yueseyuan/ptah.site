'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';

interface Client {
  id: number;
  first_name: string;
  last_name: string;
}

const DIVISION_LABELS: Record<string, string> = {
  notary: 'Mobile Notary',
  credit: 'Credit Restoration',
  criminal: 'Criminal Record Relief',
  document: 'Document Preparation',
  judgment: 'Judgment & Asset Recovery',
  consulting: 'Business Consulting',
};

function NotaryFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <div className="form-group">
          <label>Document Type</label>
          <input
            value={values.document_type || ''}
            onChange={e => onChange('document_type', e.target.value)}
            placeholder="e.g., Deed, Power of Attorney, Affidavit"
          />
        </div>
        <div className="form-group">
          <label>Number of Signers</label>
          <input
            type="number"
            min="1"
            value={values.num_signers || ''}
            onChange={e => onChange('num_signers', e.target.value)}
            placeholder="1"
          />
        </div>
      </div>
      <div className="form-group">
        <label>Travel Address</label>
        <input
          value={values.travel_address || ''}
          onChange={e => onChange('travel_address', e.target.value)}
          placeholder="Full address for mobile visit"
        />
      </div>
      <div className="form-group">
        <label>Appointment Time</label>
        <input
          type="datetime-local"
          value={values.appointment_time || ''}
          onChange={e => onChange('appointment_time', e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>Identity Documents Ready?</label>
        <select
          value={values.identity_docs_ready || ''}
          onChange={e => onChange('identity_docs_ready', e.target.value)}
        >
          <option value="">— Select —</option>
          <option value="yes">Yes — ready</option>
          <option value="no">No — need guidance</option>
          <option value="partial">Partial — some docs available</option>
        </select>
      </div>
    </>
  );
}

function CriminalFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <div className="form-group">
          <label>Offense Type</label>
          <input
            value={values.offense_type || ''}
            onChange={e => onChange('offense_type', e.target.value)}
            placeholder="e.g., Misdemeanor, Felony, Infraction"
          />
        </div>
        <div className="form-group">
          <label>Case Year</label>
          <input
            type="number"
            value={values.case_year || ''}
            onChange={e => onChange('case_year', e.target.value)}
            placeholder="e.g., 2018"
          />
        </div>
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Court</label>
          <input
            value={values.court || ''}
            onChange={e => onChange('court', e.target.value)}
            placeholder="Name of court"
          />
        </div>
        <div className="form-group">
          <label>County</label>
          <input
            value={values.county || ''}
            onChange={e => onChange('county', e.target.value)}
            placeholder="County where case was heard"
          />
        </div>
      </div>
      <div className="form-group">
        <label>Goal</label>
        <select
          value={values.goal || ''}
          onChange={e => onChange('goal', e.target.value)}
        >
          <option value="">— Select Goal —</option>
          <option value="expungement">Expungement</option>
          <option value="pardon">Pardon</option>
          <option value="sealing">Record Sealing</option>
          <option value="reduction">Charge Reduction</option>
          <option value="other">Other / Multiple</option>
        </select>
      </div>
      <div className="form-group">
        <label>Current Employment Impact</label>
        <textarea
          rows={2}
          value={values.current_employment_impact || ''}
          onChange={e => onChange('current_employment_impact', e.target.value)}
          placeholder="Describe how the record is currently affecting employment or housing…"
        />
      </div>
    </>
  );
}

function DocumentFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="form-group">
        <label>Document Needed</label>
        <input
          value={values.document_needed || ''}
          onChange={e => onChange('document_needed', e.target.value)}
          placeholder="e.g., Cease & Desist Letter, Promissory Note, Affidavit of Facts"
        />
      </div>
      <div className="form-group">
        <label>Purpose</label>
        <textarea
          rows={2}
          value={values.purpose || ''}
          onChange={e => onChange('purpose', e.target.value)}
          placeholder="What is this document intended to accomplish?"
        />
      </div>
      <div className="form-group">
        <label>Parties Involved</label>
        <input
          value={values.parties_involved || ''}
          onChange={e => onChange('parties_involved', e.target.value)}
          placeholder="Names of all parties (buyer, seller, creditor, debtor, etc.)"
        />
      </div>
      <div className="form-group">
        <label>Deadline</label>
        <input
          type="date"
          value={values.deadline || ''}
          onChange={e => onChange('deadline', e.target.value)}
        />
      </div>
    </>
  );
}

function JudgmentFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <div className="form-group">
          <label>Judgment Amount ($)</label>
          <input
            type="number"
            step="0.01"
            value={values.judgment_amount || ''}
            onChange={e => onChange('judgment_amount', e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="form-group">
          <label>Judgment Date</label>
          <input
            type="date"
            value={values.judgment_date || ''}
            onChange={e => onChange('judgment_date', e.target.value)}
          />
        </div>
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Court</label>
          <input
            value={values.court || ''}
            onChange={e => onChange('court', e.target.value)}
            placeholder="Court that issued the judgment"
          />
        </div>
        <div className="form-group">
          <label>Debtor Name</label>
          <input
            value={values.debtor_name || ''}
            onChange={e => onChange('debtor_name', e.target.value)}
            placeholder="Full name of debtor"
          />
        </div>
      </div>
      <div className="form-group">
        <label>Known Assets</label>
        <textarea
          rows={2}
          value={values.known_assets || ''}
          onChange={e => onChange('known_assets', e.target.value)}
          placeholder="List any known assets: bank accounts, vehicles, real property, employer…"
        />
      </div>
    </>
  );
}

function ConsultingFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <div className="form-group">
          <label>Business Type</label>
          <input
            value={values.business_type || ''}
            onChange={e => onChange('business_type', e.target.value)}
            placeholder="e.g., LLC, Sole Prop, S-Corp, Non-profit"
          />
        </div>
        <div className="form-group">
          <label>Stage</label>
          <select
            value={values.stage || ''}
            onChange={e => onChange('stage', e.target.value)}
          >
            <option value="">— Select Stage —</option>
            <option value="startup">Startup — not yet launched</option>
            <option value="existing">Existing — already operating</option>
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>Primary Need</label>
        <input
          value={values.primary_need || ''}
          onChange={e => onChange('primary_need', e.target.value)}
          placeholder="e.g., Formation, Business Plan, SOPs, Funding Strategy"
        />
      </div>
      <div className="form-group">
        <label>Revenue Range</label>
        <select
          value={values.revenue_range || ''}
          onChange={e => onChange('revenue_range', e.target.value)}
        >
          <option value="">— Select Range —</option>
          <option value="pre_revenue">Pre-revenue</option>
          <option value="under_50k">Under $50K / year</option>
          <option value="50k_250k">$50K – $250K / year</option>
          <option value="250k_1m">$250K – $1M / year</option>
          <option value="over_1m">Over $1M / year</option>
        </select>
      </div>
    </>
  );
}

export default function NewServiceCasePage() {
  const { division } = useParams<{ division: string }>();
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [clientId, setClientId] = useState('');
  const [notes, setNotes] = useState('');
  const [intakeData, setIntakeData] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const divisionLabel = DIVISION_LABELS[division] || division;

  useEffect(() => {
    const token = localStorage.getItem('token') || localStorage.getItem('aegis_token');
    fetch('/api/clients/', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : [])
      .then(setClients)
      .catch(() => {});
  }, []);

  function setIntakeField(key: string, value: string) {
    setIntakeData(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId) { setError('Please select a client.'); return; }
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('aegis_token');
      const res = await fetch('/api/service-cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          division_slug: division,
          client_id: parseInt(clientId),
          notes,
          intake_data: intakeData,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      router.push(`/services/${division}/${data.id}`);
    } catch (err: unknown) {
      const e = err as Error;
      setError(e.message || 'Failed to create case.');
    } finally {
      setLoading(false);
    }
  }

  function renderIntakeFields() {
    switch (division) {
      case 'notary':
        return <NotaryFields values={intakeData} onChange={setIntakeField} />;
      case 'criminal':
        return <CriminalFields values={intakeData} onChange={setIntakeField} />;
      case 'document':
        return <DocumentFields values={intakeData} onChange={setIntakeField} />;
      case 'judgment':
        return <JudgmentFields values={intakeData} onChange={setIntakeField} />;
      case 'consulting':
        return <ConsultingFields values={intakeData} onChange={setIntakeField} />;
      default:
        return (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>
            No specific intake fields for this division. Add details in the Notes field.
          </p>
        );
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Link href="/services" style={{ fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
              Services
            </Link>
            <span style={{ color: 'var(--muted)', fontSize: 12 }}>/</span>
            <Link href={`/services/${division}`} style={{ fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
              {divisionLabel}
            </Link>
            <span style={{ color: 'var(--muted)', fontSize: 12 }}>/</span>
            <span style={{ fontSize: 12 }}>New Case</span>
          </div>
          <h1>New {divisionLabel} Case</h1>
          <p>Complete the intake form to open a new case</p>
        </div>

        <form onSubmit={handleSubmit} style={{ maxWidth: 680 }}>
          {/* Client selection */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Client</h3>
            <div className="form-group">
              <label>Select Client *</label>
              <select
                value={clientId}
                onChange={e => setClientId(e.target.value)}
                required
              >
                <option value="">— Select a Client —</option>
                {clients.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Division-specific intake fields */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Intake Information</h3>
            {renderIntakeFields()}
          </div>

          {/* Notes */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Internal Notes</h3>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <textarea
                rows={3}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Any additional notes for this case (internal use only)…"
              />
            </div>
          </div>

          {error && <div className="alert-error">{error}</div>}

          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create Case'}
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => router.back()}
            >
              Cancel
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
