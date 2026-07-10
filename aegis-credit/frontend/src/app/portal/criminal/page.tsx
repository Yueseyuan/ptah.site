'use client';
import { useState } from 'react';
import { getPortalToken } from '@/lib/portal-api';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
];

const RECORD_TYPES = [
  { value: 'arrest', label: 'Arrest — No Conviction', desc: 'Arrested but charges dropped, dismissed, or no indictment' },
  { value: 'misdemeanor', label: 'Misdemeanor Conviction', desc: 'Convicted of a misdemeanor offense' },
  { value: 'felony', label: 'Felony Conviction', desc: 'Convicted of a felony offense' },
  { value: 'juvenile', label: 'Juvenile Record', desc: 'Record from when you were under 18' },
  { value: 'civil', label: 'Civil / Other Record', desc: 'Civil judgment, order of protection, or other non-criminal record' },
];

interface ChecklistItem { item: string; required: boolean; }
interface Result {
  case_number: string;
  checklist: ChecklistItem[];
  next_steps: string[];
}

export default function CriminalPortalPage() {
  const [step, setStep] = useState<'form' | 'submitted'>('form');
  const [form, setForm] = useState({
    state: 'SC',
    record_type: '',
    charge: '',
    charge_year: '',
    county: '',
    case_number_field: '',
    outcome: '',
    notes: '',
  });
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function set(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.record_type) { setError('Please select a record type.'); return; }
    if (!form.charge) { setError('Please describe the charge.'); return; }
    setError('');
    setLoading(true);
    try {
      const token = getPortalToken();
      const res = await fetch('/api/portal/service-intake', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          division_slug: 'criminal',
          title: `Criminal Record Relief — ${form.charge}`,
          intake_data: {
            state: form.state,
            record_type: form.record_type,
            charge: form.charge,
            charge_year: form.charge_year,
            county: form.county,
            case_number: form.case_number_field,
            outcome: form.outcome,
            notes: form.notes,
          },
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Submission failed');
      }
      const data = await res.json();
      setResult(data);
      setStep('submitted');
    } catch (err: unknown) {
      setError((err as Error).message || 'Submission failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (step === 'submitted' && result) {
    return (
      <div>
        <div style={{
          background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 12,
          padding: '24px 28px', marginBottom: 28,
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
            Case Received
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#14532d', marginBottom: 4 }}>
            {result.case_number}
          </div>
          <div style={{ fontSize: 14, color: '#166534' }}>
            Your Criminal Record Relief intake has been submitted. We&apos;ll review your information within 1-2 business days.
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
          {/* Checklist */}
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>
              Documents to Gather
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {result.checklist.map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: 4, border: '2px solid #d1d5db',
                    flexShrink: 0, marginTop: 1,
                  }} />
                  <div>
                    <span style={{ fontSize: 13, color: '#374151' }}>{item.item}</span>
                    {item.required && (
                      <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 700, marginLeft: 6 }}>Required</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Next Steps */}
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>
              What Happens Next
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {result.next_steps.map((step, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <div style={{
                    width: 22, height: 22, borderRadius: '50%', background: '#0a2540',
                    color: '#fff', fontSize: 11, fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    {i + 1}
                  </div>
                  <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.55, margin: 0 }}>{step}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <a href="/portal/dashboard" style={{
            background: '#0a2540', color: '#fff', padding: '10px 22px',
            borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
          }}>
            Back to Dashboard
          </a>
          <a href="/portal/documents" style={{
            background: 'transparent', color: '#1d4ed8', padding: '10px 22px',
            borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
            border: '1px solid #bfdbfe',
          }}>
            Upload Documents
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
          Criminal Record Relief
        </div>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>
          Expungement &amp; Record Sealing Intake
        </h2>
        <p style={{ color: '#64748b', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
          Complete the form below to start your eligibility review. We'll assess your record
          under your state's expungement statutes and outline a clear path forward.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, alignItems: 'flex-start' }}>
        <form onSubmit={handleSubmit}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 28px', marginBottom: 16 }}>
            {error && (
              <div style={{
                background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
                borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14,
              }}>
                {error}
              </div>
            )}

            <SectionLabel>Record Information</SectionLabel>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>State where the record exists *</label>
              <select value={form.state} onChange={e => set('state', e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Type of record *</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {RECORD_TYPES.map(rt => (
                  <label key={rt.value} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 10,
                    padding: '10px 14px', borderRadius: 8, cursor: 'pointer',
                    border: `2px solid ${form.record_type === rt.value ? '#0a2540' : '#e2e8f0'}`,
                    background: form.record_type === rt.value ? '#f0f4ff' : '#fff',
                  }}>
                    <input
                      type="radio"
                      name="record_type"
                      value={rt.value}
                      checked={form.record_type === rt.value}
                      onChange={() => set('record_type', rt.value)}
                      style={{ marginTop: 2 }}
                    />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#0a2540' }}>{rt.label}</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>{rt.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <Field label="Charge / Offense Description *" value={form.charge} onChange={v => set('charge', v)} placeholder="e.g. Simple Possession, Petit Larceny" required />
            <div style={{ display: 'flex', gap: 12 }}>
              <Field label="Year of Offense / Arrest" value={form.charge_year} onChange={v => set('charge_year', v)} placeholder="e.g. 2019" style={{ flex: 1 }} />
              <Field label="County" value={form.county} onChange={v => set('county', v)} placeholder="e.g. Greenville" style={{ flex: 1 }} />
            </div>
            <Field label="Court Case Number (if known)" value={form.case_number_field} onChange={v => set('case_number_field', v)} placeholder="e.g. 2019-GS-00-12345" />
            <Field label="Case Outcome / Disposition" value={form.outcome} onChange={v => set('outcome', v)} placeholder="e.g. Dismissed, Guilty plea, Nolo contendere, Not guilty" />

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Additional notes (optional)</label>
              <textarea
                value={form.notes}
                onChange={e => set('notes', e.target.value)}
                placeholder="Anything else we should know — probation completion, multiple charges, related records in other states..."
                rows={3}
                style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>

            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? 'Submitting…' : 'Submit Intake & Get My Checklist →'}
            </button>
          </div>
        </form>

        {/* Sidebar */}
        <div>
          <div style={{ background: '#0a2540', borderRadius: 12, padding: '20px 20px', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#c9a84c', marginBottom: 12 }}>What We Prepare</div>
            {['Expungement petitions', 'Record sealing motions', 'Pardons & clemency support', 'Court filing packets', 'Eligibility analysis'].map(i => (
              <div key={i} style={{ fontSize: 12, color: '#ccd6f6', marginBottom: 7, display: 'flex', gap: 8 }}>
                <span style={{ color: '#c9a84c' }}>›</span>{i}
              </div>
            ))}
          </div>
          <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 12, padding: '16px 18px' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#9a3412', marginBottom: 6 }}>Not a law firm</div>
            <p style={{ fontSize: 11, color: '#c2410c', lineHeight: 1.6, margin: 0 }}>
              We prepare documents and provide information — we are not attorneys and do not provide legal advice.
              For complex felony matters, we will recommend an attorney referral.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
      letterSpacing: 0.8, marginBottom: 14, borderBottom: '1px solid #f1f5f9', paddingBottom: 6,
    }}>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, placeholder, required, type = 'text', style }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; type?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{ marginBottom: 14, ...style }}>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
      />
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5,
};
const inputStyle: React.CSSProperties = {
  padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8,
  fontSize: 14, outline: 'none', fontFamily: 'system-ui, sans-serif',
};
const btnStyle: React.CSSProperties = {
  width: '100%', background: '#0a2540', color: '#fff', border: 'none',
  borderRadius: 8, padding: '13px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer',
};
