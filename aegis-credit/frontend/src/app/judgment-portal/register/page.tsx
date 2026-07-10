'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const CASE_TYPES = [
  'Unpaid court judgment',
  'Hidden / transferred assets',
  'Landlord — tenant owes money',
  'Business — unpaid invoices',
  'Estate / unclaimed property',
  'Divorce — hidden assets',
  'Other',
];

export default function JudgmentPortalRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    case_type: '', password: '', confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function setf(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm_password) { setError('Passwords do not match.'); return; }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/portal/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          phone: form.phone || undefined,
          username: form.email,
          password: form.password,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Registration failed.');
      }
      const data = await res.json();
      localStorage.setItem('judgment_token', (data as { access_token?: string }).access_token || '');
      localStorage.setItem('judgment_role', 'client');
      router.replace('/judgment-portal/dashboard');
    } catch (err: unknown) {
      setError((err as Error).message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#1c1917',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 460 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <a href="/judgment-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 26, marginBottom: 6 }}>⚖️</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#fff' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#C9A84C', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Recovery — New Client</div>
          </a>
        </div>

        <div style={{ background: '#fff', borderRadius: 14, padding: '28px 28px', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1c1917', margin: '0 0 20px' }}>Create your recovery account</h2>

          {error && (
            <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>
          )}

          <form onSubmit={handleSubmit}>
            <SectionLabel>Your Information</SectionLabel>
            <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
              <Field label="First Name *" value={form.first_name} onChange={v => setf('first_name', v)} required style={{ flex: 1 }} />
              <Field label="Last Name *" value={form.last_name} onChange={v => setf('last_name', v)} required style={{ flex: 1 }} />
            </div>
            <Field label="Email Address *" value={form.email} onChange={v => setf('email', v)} type="email" required />
            <Field label="Phone Number" value={form.phone} onChange={v => setf('phone', v)} placeholder="(555) 000-0000" />

            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Type of Case</label>
              <select value={form.case_type} onChange={e => setf('case_type', e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                <option value="">Select your situation…</option>
                {CASE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <SectionLabel style={{ marginTop: 8 }}>Set Password</SectionLabel>
            <Field label="Password *" value={form.password} onChange={v => setf('password', v)} type="password" required placeholder="8+ characters" />
            <Field label="Confirm Password *" value={form.confirm_password} onChange={v => setf('confirm_password', v)} type="password" required />

            <button type="submit" disabled={loading} style={{ ...btnStyle, marginTop: 8 }}>
              {loading ? 'Creating account…' : 'Create Account →'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#57534e' }}>
          Already have an account?{' '}
          <a href="/judgment-portal/login" style={{ color: '#C9A84C', fontWeight: 600, textDecoration: 'none' }}>Sign in</a>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12, borderBottom: '1px solid #f1f5f9', paddingBottom: 5, ...style }}>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder, required, style }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean; style?: React.CSSProperties;
}) {
  return (
    <div style={{ marginBottom: 14, ...style }}>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required={required}
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }} />
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 4 };
const inputStyle: React.CSSProperties = { padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: 'system-ui, sans-serif' };
const btnStyle: React.CSSProperties = { width: '100%', background: '#C9A84C', color: '#1c1917', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 800, cursor: 'pointer' };
