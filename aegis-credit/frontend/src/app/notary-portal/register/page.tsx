'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { notaryRegister, setNotaryAuth } from '@/lib/notary-api';

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'];

export default function NotaryRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm_password: '',
    phone: '', license_number: '', license_state: '', license_expires: '',
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
    setError('');
    setLoading(true);
    try {
      const data = await notaryRegister({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        phone: form.phone || undefined,
        license_number: form.license_number || undefined,
        license_state: form.license_state || undefined,
        license_expires: form.license_expires || undefined,
      });
      setNotaryAuth(data.access_token, 'notary');
      router.replace('/notary-portal/dashboard');
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#f0f4f8',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <a href="/notary-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 26, marginBottom: 6 }}>🖊️</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#0f2d52' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Notary Registration</div>
          </a>
        </div>

        <div style={{ background: '#fff', borderRadius: 14, padding: '28px 28px', boxShadow: '0 2px 16px rgba(0,0,0,0.08)' }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: '#0f2d52', margin: '0 0 20px' }}>Create your notary account</h2>

          {error && (
            <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>
          )}

          <form onSubmit={handleSubmit}>
            <SectionLabel>Personal Information</SectionLabel>
            <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
              <Field label="First Name *" value={form.first_name} onChange={v => setf('first_name', v)} required style={{ flex: 1 }} />
              <Field label="Last Name *" value={form.last_name} onChange={v => setf('last_name', v)} required style={{ flex: 1 }} />
            </div>
            <Field label="Email Address *" value={form.email} onChange={v => setf('email', v)} type="email" required />
            <Field label="Phone Number" value={form.phone} onChange={v => setf('phone', v)} placeholder="(555) 000-0000" />

            <SectionLabel style={{ marginTop: 8 }}>Set Password</SectionLabel>
            <Field label="Password *" value={form.password} onChange={v => setf('password', v)} type="password" required placeholder="8+ characters" />
            <Field label="Confirm Password *" value={form.confirm_password} onChange={v => setf('confirm_password', v)} type="password" required />

            <SectionLabel style={{ marginTop: 8 }}>Notary License (optional — can add later)</SectionLabel>
            <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
              <Field label="License Number" value={form.license_number} onChange={v => setf('license_number', v)} style={{ flex: 2 }} />
              <div style={{ flex: 1, marginBottom: 0 }}>
                <label style={labelStyle}>State</label>
                <select value={form.license_state} onChange={e => setf('license_state', e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="">—</option>
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <Field label="License Expiration" value={form.license_expires} onChange={v => setf('license_expires', v)} type="date" />

            <button type="submit" disabled={loading} style={{ ...btnStyle, marginTop: 8 }}>
              {loading ? 'Creating account…' : 'Create Account →'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#64748b' }}>
          Already have an account?{' '}
          <a href="/notary-portal/login" style={{ color: '#0f2d52', fontWeight: 600, textDecoration: 'none' }}>Sign in</a>
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
const btnStyle: React.CSSProperties = { width: '100%', background: '#0f2d52', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' };
