'use client';
import { useState } from 'react';

const CASE_TYPES = [
  { value: 'judgment_enforcement', label: 'Court Judgment — Need to Collect', icon: '⚖️' },
  { value: 'asset_tracing', label: 'Hidden / Transferred Assets', icon: '🔍' },
  { value: 'landlord_tenant', label: 'Landlord — Tenant Owes Money', icon: '🏠' },
  { value: 'business_debt', label: 'Business — Unpaid Invoices / Bad Debt', icon: '🏪' },
  { value: 'estate_recovery', label: 'Estate / Unclaimed Property', icon: '📂' },
  { value: 'divorce_assets', label: 'Divorce — Hidden Assets', icon: '👥' },
];

interface Result { case_number: string; checklist: { item: string; required: boolean }[]; next_steps: string[] }

export default function JudgmentIntakePage() {
  const [form, setForm] = useState({
    case_type: '', debtor_name: '', amount_owed: '', judgment_state: '',
    has_judgment: '', judgment_date: '', debtor_employer: '',
    debtor_property: '', notes: '',
  });
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function setf(k: string, v: string) { setForm(p => ({ ...p, [k]: v })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.case_type) { setError('Please select a case type.'); return; }
    if (!form.amount_owed) { setError('Please enter the amount owed.'); return; }
    setError(''); setLoading(true);
    try {
      const token = localStorage.getItem('judgment_token');
      const res = await fetch('/api/portal/service-intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          division_slug: 'judgment',
          title: `${CASE_TYPES.find(c => c.value === form.case_type)?.label || form.case_type} — $${form.amount_owed}`,
          intake_data: form,
        }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Submission failed');
      setResult(await res.json());
    } catch (err: unknown) {
      setError((err as Error).message || 'Submission failed.');
    } finally { setLoading(false); }
  }

  if (result) return (
    <div>
      <div style={{ background: '#fefce8', border: '1px solid #fde68a', borderRadius: 12, padding: '22px 26px', marginBottom: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#92400e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Case Opened</div>
        <div style={{ fontSize: 22, fontWeight: 800, color: '#78350f', marginBottom: 4 }}>{result.case_number}</div>
        <div style={{ fontSize: 14, color: '#92400e' }}>We&apos;ll review your case and contact you within 1 business day to discuss recovery strategy.</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 20 }}>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1c1917', margin: '0 0 14px' }}>Documents to Gather</h3>
          {result.checklist.map((item, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10 }}>
              <div style={{ width: 18, height: 18, borderRadius: 3, border: '2px solid #d1d5db', flexShrink: 0, marginTop: 2 }} />
              <div>
                <span style={{ fontSize: 13, color: '#374151' }}>{item.item}</span>
                {item.required && <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 700, marginLeft: 6 }}>Required</span>}
              </div>
            </div>
          ))}
        </div>
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1c1917', margin: '0 0 14px' }}>What Happens Next</h3>
          {result.next_steps.map((s, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 12 }}>
              <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#C9A84C', color: '#1c1917', fontSize: 10, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{i + 1}</div>
              <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.55, margin: 0 }}>{s}</p>
            </div>
          ))}
        </div>
      </div>
      <a href="/judgment-portal/dashboard" style={{ background: '#C9A84C', color: '#1c1917', padding: '11px 24px', borderRadius: 8, fontSize: 13, fontWeight: 800, textDecoration: 'none', display: 'inline-block' }}>
        View My Cases →
      </a>
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: 26 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#C9A84C', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Recovery Intake</div>
        <h2 style={{ color: '#1c1917', fontSize: 21, fontWeight: 800, margin: '0 0 8px' }}>Tell Us About Your Case</h2>
        <p style={{ color: '#64748b', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
          We&apos;ll review the details, assess recoverability, and reach out within 1 business day with a strategy.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {error && <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>}

        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 26px', marginBottom: 14 }}>
          <SectionLabel>What Are You Trying to Recover? *</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10, marginBottom: 22 }}>
            {CASE_TYPES.map(ct => (
              <label key={ct.value} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '11px 14px',
                borderRadius: 8, cursor: 'pointer',
                border: `2px solid ${form.case_type === ct.value ? '#C9A84C' : '#e2e8f0'}`,
                background: form.case_type === ct.value ? '#fefce8' : '#fff',
              }}>
                <input type="radio" name="case_type" value={ct.value} checked={form.case_type === ct.value} onChange={() => setf('case_type', ct.value)} />
                <span style={{ fontSize: 16 }}>{ct.icon}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#1c1917' }}>{ct.label}</span>
              </label>
            ))}
          </div>

          <SectionLabel>Case Details</SectionLabel>
          <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
            <Field label="Debtor / Party Name *" value={form.debtor_name} onChange={v => setf('debtor_name', v)} required placeholder="Person or business that owes you" style={{ flex: 2 }} />
            <Field label="Amount Owed *" value={form.amount_owed} onChange={v => setf('amount_owed', v)} required placeholder="e.g. $12,500" style={{ flex: 1 }} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Do you have a court judgment?</label>
              <select value={form.has_judgment} onChange={e => setf('has_judgment', e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                <option value="">Select…</option>
                <option value="yes">Yes — judgment entered</option>
                <option value="no">No — not yet</option>
                <option value="partial">Partial — some paid</option>
              </select>
            </div>
            <Field label="Judgment Date (if any)" value={form.judgment_date} onChange={v => setf('judgment_date', v)} type="date" style={{ flex: 1 }} />
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>State of Judgment / Debt</label>
              <input type="text" value={form.judgment_state} onChange={e => setf('judgment_state', e.target.value)} placeholder="e.g. SC" style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }} />
            </div>
          </div>

          <SectionLabel>What Do You Know About the Debtor?</SectionLabel>
          <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
            <Field label="Employer / Income Source" value={form.debtor_employer} onChange={v => setf('debtor_employer', v)} placeholder="Employer name or 'unknown'" style={{ flex: 1 }} />
            <Field label="Known Property / Assets" value={form.debtor_property} onChange={v => setf('debtor_property', v)} placeholder="Home, car, bank, business..." style={{ flex: 1 }} />
          </div>

          <div>
            <label style={labelStyle}>Additional Details</label>
            <textarea value={form.notes} onChange={e => setf('notes', e.target.value)}
              placeholder="Any other context — prior attempts to collect, known addresses, related parties, transfers you suspect..."
              rows={3} style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' as const }} />
          </div>
        </div>

        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? 'Submitting…' : 'Submit Recovery Case →'}
        </button>
      </form>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14, borderBottom: '1px solid #f1f5f9', paddingBottom: 6 }}>{children}</div>;
}
function Field({ label, value, onChange, type = 'text', placeholder, required, style }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean; style?: React.CSSProperties;
}) {
  return (
    <div style={{ marginBottom: 0, ...style }}>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required={required}
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }} />
    </div>
  );
}
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 5 };
const inputStyle: React.CSSProperties = { padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: 'system-ui, sans-serif' };
const btnStyle: React.CSSProperties = { width: '100%', background: '#1c1917', color: '#C9A84C', border: 'none', borderRadius: 8, padding: '13px 0', fontSize: 15, fontWeight: 800, cursor: 'pointer' };
