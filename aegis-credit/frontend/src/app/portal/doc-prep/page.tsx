'use client';
import { useState } from 'react';
import { getPortalToken } from '@/lib/portal-api';

const DOC_TYPES = [
  { value: 'llc_formation', label: 'LLC Formation', desc: 'Articles of Organization + EIN guidance', est: '$150–$250', turn: '3-5 days' },
  { value: 'operating_agreement', label: 'Operating Agreement', desc: 'Member-managed or manager-managed LLC structure', est: '$100–$175', turn: '2-4 days' },
  { value: 'demand_letter', label: 'Demand Letter', desc: 'Debt collection, contract breach, or dispute', est: '$75–$125', turn: '1-2 days' },
  { value: 'power_of_attorney', label: 'Power of Attorney', desc: 'General, financial, or limited POA', est: '$75–$125', turn: '1-3 days' },
  { value: 'lease_agreement', label: 'Lease Agreement', desc: 'Residential or commercial property lease', est: '$100–$200', turn: '2-4 days' },
  { value: 'contract', label: 'Service / Business Contract', desc: 'Client agreements, vendor contracts, freelance terms', est: '$100–$175', turn: '2-4 days' },
  { value: 'affidavit', label: 'Affidavit / Sworn Statement', desc: 'Notarized sworn testimony document', est: '$50–$75', turn: '1-2 days' },
  { value: 'other', label: 'Other Document', desc: 'Tell us what you need', est: 'Quote provided', turn: 'Varies' },
];

interface ChecklistItem { item: string; required: boolean; }
interface Result {
  case_number: string;
  checklist: ChecklistItem[];
  next_steps: string[];
}

export default function DocPrepPortalPage() {
  const [step, setStep] = useState<'form' | 'submitted'>('form');
  const [selected, setSelected] = useState('');
  const [form, setForm] = useState({
    purpose: '',
    parties: '',
    state: 'SC',
    deadline: '',
    notes: '',
  });
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selectedType = DOC_TYPES.find(d => d.value === selected);

  function setf(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) { setError('Please select a document type.'); return; }
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
          division_slug: 'document',
          title: `Document Prep — ${selectedType?.label}`,
          intake_data: {
            doc_type: selected,
            purpose: form.purpose,
            parties: form.parties,
            state: form.state,
            deadline: form.deadline,
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
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 12, padding: '24px 28px', marginBottom: 28 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Request Received</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#14532d', marginBottom: 4 }}>{result.case_number}</div>
          <div style={{ fontSize: 14, color: '#166534' }}>
            Your document preparation request is in. We&apos;ll confirm scope and any questions within 1 business day.
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>Information to Prepare</h3>
            {result.checklist.map((item, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10 }}>
                <div style={{ width: 20, height: 20, borderRadius: 4, border: '2px solid #d1d5db', flexShrink: 0, marginTop: 1 }} />
                <div>
                  <span style={{ fontSize: 13, color: '#374151' }}>{item.item}</span>
                  {item.required && <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 700, marginLeft: 6 }}>Required</span>}
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>What Happens Next</h3>
            {result.next_steps.map((s, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12 }}>
                <div style={{ width: 22, height: 22, borderRadius: '50%', background: '#0a2540', color: '#fff', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{i + 1}</div>
                <p style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.55, margin: 0 }}>{s}</p>
              </div>
            ))}
          </div>
        </div>

        <a href="/portal/dashboard" style={{ background: '#0a2540', color: '#fff', padding: '10px 22px', borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none', display: 'inline-block' }}>
          Back to Dashboard
        </a>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Document Preparation</div>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>Request a Document</h2>
        <p style={{ color: '#64748b', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
          Select the document type below and fill in the details. We&apos;ll confirm scope, provide a firm quote, and deliver a ready-to-sign document.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {error && (
          <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14 }}>{error}</div>
        )}

        {/* Document type picker */}
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 28px', marginBottom: 16 }}>
          <SectionLabel>Select Document Type *</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
            {DOC_TYPES.map(dt => (
              <label key={dt.value} style={{
                display: 'flex', flexDirection: 'column', gap: 4,
                padding: '14px 16px', borderRadius: 8, cursor: 'pointer',
                border: `2px solid ${selected === dt.value ? '#0a2540' : '#e2e8f0'}`,
                background: selected === dt.value ? '#f0f4ff' : '#fff',
                transition: 'all 0.1s',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="radio" name="doc_type" value={dt.value} checked={selected === dt.value} onChange={() => setSelected(dt.value)} style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#0a2540' }}>{dt.label}</span>
                </div>
                <span style={{ fontSize: 11, color: '#64748b', paddingLeft: 20 }}>{dt.desc}</span>
                <div style={{ display: 'flex', gap: 12, paddingLeft: 20, marginTop: 2 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#16a34a' }}>{dt.est}</span>
                  <span style={{ fontSize: 10, color: '#94a3b8' }}>{dt.turn}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Details */}
        {selected && (
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 28px', marginBottom: 16 }}>
            <SectionLabel>Document Details</SectionLabel>
            <Field label="Purpose / Context *" value={form.purpose} onChange={v => setf('purpose', v)} placeholder={
              selected === 'demand_letter' ? 'e.g. Contractor failed to complete work, owed $3,200' :
              selected === 'llc_formation' ? 'e.g. Starting a landscaping business in SC' :
              selected === 'lease_agreement' ? 'e.g. Renting a 2BR residential unit in Greenville SC' :
              'Briefly describe what this document is for'
            } required />
            <Field label="Parties Involved *" value={form.parties} onChange={v => setf('parties', v)} placeholder="e.g. John Smith (landlord) and Jane Doe (tenant)" required />
            <div style={{ display: 'flex', gap: 12 }}>
              <Field label="State" value={form.state} onChange={v => setf('state', v)} placeholder="SC" style={{ flex: 0.5 }} />
              <Field label="Deadline (if any)" value={form.deadline} onChange={v => setf('deadline', v)} placeholder="e.g. Need by July 20" style={{ flex: 1 }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Additional notes</label>
              <textarea
                value={form.notes}
                onChange={e => setf('notes', e.target.value)}
                placeholder="Any specific terms, conditions, or context we should know..."
                rows={3}
                style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>
          </div>
        )}

        <button type="submit" disabled={loading || !selected} style={{
          ...btnStyle,
          opacity: !selected ? 0.5 : 1,
          cursor: !selected ? 'not-allowed' : 'pointer',
        }}>
          {loading ? 'Submitting…' : 'Submit Request & Get Quote →'}
        </button>
      </form>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 14, borderBottom: '1px solid #f1f5f9', paddingBottom: 6 }}>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, placeholder, required, style }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; style?: React.CSSProperties;
}) {
  return (
    <div style={{ marginBottom: 14, ...style }}>
      <label style={labelStyle}>{label}</label>
      <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required={required}
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }} />
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 };
const inputStyle: React.CSSProperties = { padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: 'system-ui, sans-serif' };
const btnStyle: React.CSSProperties = { background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8, padding: '13px 28px', fontSize: 15, fontWeight: 600, width: '100%' };
