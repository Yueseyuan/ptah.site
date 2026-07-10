'use client';
import { useState } from 'react';
import { getPortalToken } from '@/lib/portal-api';

const ENTITY_TYPES = ['Sole Proprietor', 'LLC', 'S-Corp', 'C-Corp', 'Partnership', 'Non-Profit', 'Not yet formed'];
const STAGES = [
  { value: 'idea', label: 'Idea Stage', desc: 'Haven\'t started yet, figuring out the structure' },
  { value: 'startup', label: 'Startup (0-1 yr)', desc: 'Recently launched, getting early traction' },
  { value: 'growth', label: 'Growth (1-3 yrs)', desc: 'Established and trying to scale' },
  { value: 'established', label: 'Established (3+ yrs)', desc: 'Profitable and looking to optimize or exit' },
];
const GOALS = [
  { value: 'entity_setup', label: 'Entity Setup & Formation', icon: '🏢' },
  { value: 'credit_building', label: 'Business Credit Building', icon: '📈' },
  { value: 'compliance', label: 'Compliance & Licensing', icon: '✅' },
  { value: 'growth_plan', label: '90-Day Growth Plan', icon: '🚀' },
  { value: 'funding', label: 'Funding & Capital Strategy', icon: '💰' },
  { value: 'systems', label: 'Operational Systems', icon: '⚙️' },
];

interface ChecklistItem { item: string; required: boolean; }
interface Result {
  case_number: string;
  checklist: ChecklistItem[];
  next_steps: string[];
}

export default function ConsultingPortalPage() {
  const [step, setStep] = useState<'form' | 'submitted'>('form');
  const [form, setForm] = useState({
    entity_type: '',
    stage: '',
    industry: '',
    revenue_range: '',
    employees: '',
    biggest_challenge: '',
    notes: '',
  });
  const [goals, setGoals] = useState<string[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function setf(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  function toggleGoal(val: string) {
    setGoals(prev => prev.includes(val) ? prev.filter(g => g !== val) : [...prev, val]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.stage) { setError('Please select your business stage.'); return; }
    if (goals.length === 0) { setError('Please select at least one consulting goal.'); return; }
    if (!form.biggest_challenge) { setError('Please describe your top challenge.'); return; }
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
          division_slug: 'consulting',
          title: `Business Consulting — ${STAGES.find(s => s.value === form.stage)?.label || form.stage}`,
          intake_data: {
            entity_type: form.entity_type,
            stage: form.stage,
            industry: form.industry,
            revenue_range: form.revenue_range,
            employees: form.employees,
            goals,
            biggest_challenge: form.biggest_challenge,
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
          <div style={{ fontSize: 11, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Intake Received</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#14532d', marginBottom: 4 }}>{result.case_number}</div>
          <div style={{ fontSize: 14, color: '#166534' }}>
            Your consulting intake is in. Expect a call or email within 1 business day to schedule your initial consultation.
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>Prepare for Your Consultation</h3>
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

        <div style={{ display: 'flex', gap: 12 }}>
          <a href="/portal/book" style={{ background: '#c9a84c', color: '#07090f', padding: '10px 22px', borderRadius: 8, fontSize: 13, fontWeight: 700, textDecoration: 'none', display: 'inline-block' }}>
            📅 Book Consultation Now
          </a>
          <a href="/portal/dashboard" style={{ background: 'transparent', color: '#1d4ed8', padding: '10px 22px', borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none', border: '1px solid #bfdbfe', display: 'inline-block' }}>
            Dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Business Consulting</div>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: '0 0 8px' }}>Start Your Consulting Intake</h2>
        <p style={{ color: '#64748b', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
          Tell us where your business is and where you want to go. We&apos;ll review your intake and schedule an initial consultation within 1 business day.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {error && (
          <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14 }}>{error}</div>
        )}

        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '24px 28px', marginBottom: 16 }}>
          <SectionLabel>Business Stage *</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10, marginBottom: 20 }}>
            {STAGES.map(s => (
              <label key={s.value} style={{
                display: 'flex', flexDirection: 'column', gap: 3,
                padding: '12px 14px', borderRadius: 8, cursor: 'pointer',
                border: `2px solid ${form.stage === s.value ? '#0a2540' : '#e2e8f0'}`,
                background: form.stage === s.value ? '#f0f4ff' : '#fff',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="radio" name="stage" value={s.value} checked={form.stage === s.value} onChange={() => setf('stage', s.value)} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#0a2540' }}>{s.label}</span>
                </div>
                <span style={{ fontSize: 11, color: '#64748b', paddingLeft: 20 }}>{s.desc}</span>
              </label>
            ))}
          </div>

          <SectionLabel>What are your goals? * (select all that apply)</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))', gap: 10, marginBottom: 20 }}>
            {GOALS.map(g => (
              <label key={g.value} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '11px 14px', borderRadius: 8, cursor: 'pointer',
                border: `2px solid ${goals.includes(g.value) ? '#0a2540' : '#e2e8f0'}`,
                background: goals.includes(g.value) ? '#f0f4ff' : '#fff',
              }}>
                <input type="checkbox" checked={goals.includes(g.value)} onChange={() => toggleGoal(g.value)} />
                <span style={{ fontSize: 13 }}>{g.icon}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#0a2540' }}>{g.label}</span>
              </label>
            ))}
          </div>

          <SectionLabel>Business Information</SectionLabel>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1, marginBottom: 14 }}>
              <label style={labelStyle}>Entity Type</label>
              <select value={form.entity_type} onChange={e => setf('entity_type', e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                <option value="">Select…</option>
                {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <Field label="Industry / Niche" value={form.industry} onChange={v => setf('industry', v)} placeholder="e.g. Landscaping, E-commerce, Consulting" style={{ flex: 2 }} />
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <Field label="Current Monthly Revenue" value={form.revenue_range} onChange={v => setf('revenue_range', v)} placeholder="e.g. $0, $1k-$5k, $10k+" style={{ flex: 1 }} />
            <Field label="Employees / Contractors" value={form.employees} onChange={v => setf('employees', v)} placeholder="e.g. Just me, 2 part-time" style={{ flex: 1 }} />
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Your #1 challenge right now *</label>
            <textarea
              value={form.biggest_challenge}
              onChange={e => setf('biggest_challenge', e.target.value)}
              placeholder="What's the single biggest thing holding your business back? Be specific."
              rows={3}
              required
              style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>
          <div style={{ marginBottom: 0 }}>
            <label style={labelStyle}>Anything else we should know</label>
            <textarea
              value={form.notes}
              onChange={e => setf('notes', e.target.value)}
              placeholder="Prior consulting, specific deadlines, context about your market or situation..."
              rows={2}
              style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>
        </div>

        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? 'Submitting…' : 'Submit Intake & Schedule Consultation →'}
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
const btnStyle: React.CSSProperties = { width: '100%', background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8, padding: '13px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' };
