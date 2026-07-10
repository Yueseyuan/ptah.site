'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'];

export default function CriminalPortalRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    state: 'SC', password: '', confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function setf(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
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
          state: form.state,
          password: form.password,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Registration failed.');
      }
      const data = await res.json();
      localStorage.setItem('criminal_token', data.access_token);
      localStorage.setItem('criminal_role', 'client');
      router.replace('/criminal-portal/dashboard');
    } catch (err: unknown) {
      setError((err as Error).message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#1a1a2e',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 460 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <a href="/criminal-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 26, marginBottom: 6 }}>⚖️</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#fff' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#a78bfa', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Record Relief — New Client</div>
          </a>
        </div>

        <div style={{ background: '#fff', borderRadius: 14, padding: '28px 28px', boxShadow: '0 2px 20px rgba(0,0,0,0.3)' }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1a1a2e', margin: '0 0 4px' }}>Create your client account</h2>
          <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 22px', lineHeight: 1.5 }}>
            Register to submit and track your criminal record relief case.
          </p>

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
              <label style={labelStyle}>State of Record *</label>
              <select value={form.state} onChange={e => setf('state', e.target.value)} required style={{ ...inputStyle, width: '100%' }}>
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <SectionLabel style={{ marginTop: 8 }}>Set Password</SectionLabel>
            <Field label="Password *" value={form.password} onChange={v => setf('password', v)} type="password" required placeholder="8+ characters" />
            <Field label="Confirm Password *" value={form.confirm_password} onChange={v => setf('confirm_password', v)} type="password" required />

            <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 12, color: '#6d28d9', lineHeight: 1.5 }}>
              Your information is kept strictly confidential. We will never share it without your consent.
            </div>

            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? 'Creating account…' : 'Create Account →'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#64748b' }}>
          Already have an account?{' '}
          <a href="/criminal-portal/login" style={{ color: '#c4b5fd', fontWeight: 600, textDecoration: 'none' }}>Sign in</a>
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
const btnStyle: React.CSSProperties = { width: '100%', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' };
