'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';

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
  overages: 'Tax Overage Recovery',
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

function OveragesFields({ values, onChange }: { values: Record<string, string>; onChange: (k: string, v: string) => void }) {
  return (
    <>
      <div className="grid-2">
        <div className="form-group">
          <label>County</label>
          <input
            value={values.county || ''}
            onChange={e => onChange('county', e.target.value)}
            placeholder="e.g., Duval County, FL"
          />
        </div>
        <div className="form-group">
          <label>Tax Deed Number</label>
          <input
            value={values.tax_deed_number || ''}
            onChange={e => onChange('tax_deed_number', e.target.value)}
            placeholder="e.g., 2024-TD-001234"
          />
        </div>
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Parcel / Folio Number</label>
          <input
            value={values.parcel_folio || ''}
            onChange={e => onChange('parcel_folio', e.target.value)}
            placeholder="e.g., 01-2345-678-0000"
          />
        </div>
        <div className="form-group">
          <label>Former Owner Name</label>
          <input
            value={values.owner_name || ''}
            onChange={e => onChange('owner_name', e.target.value)}
            placeholder="Name as it appears on deed"
          />
        </div>
      </div>
      <div className="form-group">
        <label>Property Description</label>
        <input
          value={values.property_description || ''}
          onChange={e => onChange('property_description', e.target.value)}
          placeholder="Street address or legal description"
        />
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Opening Bid ($)</label>
          <input
            type="number"
            step="0.01"
            value={values.opening_bid || ''}
            onChange={e => onChange('opening_bid', e.target.value)}
            placeholder="0.00"
          />
        </div>
        <div className="form-group">
          <label>Sale Price ($)</label>
          <input
            type="number"
            step="0.01"
            value={values.sale_price || ''}
            onChange={e => onChange('sale_price', e.target.value)}
            placeholder="0.00"
          />
        </div>
      </div>
      <div className="grid-2">
        <div className="form-group">
          <label>Estimated Surplus ($)</label>
          <input
            type="number"
            step="0.01"
            value={values.estimated_surplus || ''}
            onChange={e => onChange('estimated_surplus', e.target.value)}
            placeholder="Sale price minus opening bid"
          />
        </div>
        <div className="form-group">
          <label>Claim Status</label>
          <select
            value={values.claim_status || ''}
            onChange={e => onChange('claim_status', e.target.value)}
          >
            <option value="">— Select —</option>
            <option value="unclaimed">Unclaimed</option>
            <option value="in_progress">In Progress</option>
            <option value="filed">Filed with County</option>
            <option value="approved">Approved</option>
            <option value="disbursed">Disbursed</option>
            <option value="denied">Denied</option>
          </select>
        </div>
      </div>
      <div className="form-group">
        <label>Case Complexity</label>
        <select
          value={values.case_complexity || ''}
          onChange={e => onChange('case_complexity', e.target.value)}
        >
          <option value="">— Select —</option>
          <option value="simple">Simple — no known liens or competing claimants</option>
          <option value="moderate">Moderate — possible liens or locate difficulty</option>
          <option value="complex">Complex — competing claimants or legal hold</option>
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
  const [disclosureAccepted, setDisclosureAccepted] = useState(
    division !== 'judgment' && division !== 'overages'
  );
  const [disclosureChecked, setDisclosureChecked] = useState(false);

  const divisionLabel = DIVISION_LABELS[division] || division;

  useEffect(() => {
    api.get<Client[]>('/api/clients/')
      .then(r => setClients(r.data))
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
      const { data } = await api.post<{ id: number }>('/api/service-cases', {
        division_slug: division,
        client_id: parseInt(clientId),
        notes,
        intake_data: intakeData,
      });
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
      case 'overages':
        return <OveragesFields values={intakeData} onChange={setIntakeField} />;
      default:
        return (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>
            No specific intake fields for this division. Add details in the Notes field.
          </p>
        );
    }
  }

  if (!disclosureAccepted) {
    const isOverages = division === 'overages';
    return (
      <div className="main-layout">
        <Sidebar />
        <main className="main-content">
          <div className="page-header">
            <h1>Non-Lawyer Disclosure</h1>
            <p>Required before opening a {isOverages ? 'tax overage recovery' : 'commercial judgment recovery'} case</p>
          </div>
          <div className="card" style={{ maxWidth: 680 }}>
            <div style={{
              background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: 'var(--radius)',
              padding: '14px 16px', marginBottom: 20,
            }}>
              <strong style={{ fontSize: 13 }}>IMPORTANT NOTICE — PLEASE READ CAREFULLY</strong>
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text)' }}>
              <p><strong>Cruel &amp; Associates is NOT a law firm and does NOT provide legal advice or legal representation.</strong></p>
              {isOverages ? (
                <>
                  <p>
                    The Company assists former property owners in identifying and recovering tax deed surplus funds (excess proceeds)
                    from county clerks on a contingency basis. Company staff are NOT licensed attorneys and cannot:
                  </p>
                  <ul style={{ paddingLeft: 24, marginBottom: 12 }}>
                    <li>Represent clients in court or any legal proceeding</li>
                    <li>Provide legal advice on rights or obligations</li>
                    <li>Guarantee recovery of any funds</li>
                    <li>Interpret statutes, court orders, or title matters</li>
                  </ul>
                  <p>
                    Surplus fund recovery may involve competing claimants, lienholders, or other parties with legal priority.
                    You are encouraged to consult a licensed attorney if you have concerns before proceeding.
                  </p>
                </>
              ) : (
                <>
                  <p>
                    The Company provides commercial judgment recovery, asset investigation, and related administrative support services only.
                    Company staff are not licensed attorneys and cannot:
                  </p>
                  <ul style={{ paddingLeft: 24, marginBottom: 12 }}>
                    <li>Represent clients in court</li>
                    <li>Provide legal advice on rights or obligations</li>
                    <li>Interpret statutes or court orders</li>
                    <li>File documents with a court without attorney supervision</li>
                  </ul>
                  <p>
                    Clients are encouraged to consult with a licensed attorney regarding any legal questions, enforcement actions requiring court filings,
                    or matters where legal representation is required.
                  </p>
                </>
              )}
              <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 16 }}>
                This disclosure is required under applicable state law and company compliance policy.
              </p>
            </div>
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 16 }}>
              <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={disclosureChecked}
                  onChange={e => setDisclosureChecked(e.target.checked)}
                  style={{ marginTop: 3, flexShrink: 0 }}
                />
                <span>I have read and understand that Cruel &amp; Associates is NOT a law firm and does not provide legal advice or legal representation.</span>
              </label>
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button
                className="btn btn-primary"
                disabled={!disclosureChecked}
                onClick={() => setDisclosureAccepted(true)}
              >
                Accept &amp; Continue
              </button>
              <button className="btn btn-outline" onClick={() => router.back()}>
                Back
              </button>
            </div>
          </div>
        </main>
      </div>
    );
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
