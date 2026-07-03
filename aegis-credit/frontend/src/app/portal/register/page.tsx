'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { portalRegister, setPortalAuth } from '@/lib/portal-api';
import CroaDisclosure from '@/components/CroaDisclosure';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
];

export default function PortalRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    address: '', city: '', state: 'SC', zip_code: '',
    dob: '', ssn_last4: '', username: '', password: '', confirm_password: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [croaAccepted, setCroaAccepted] = useState(false);

  function set(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      const { confirm_password, ...payload } = form;
      void confirm_password;
      const data = await portalRegister(payload);
      setPortalAuth(data.access_token, data.role);
      router.push('/portal/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  if (!croaAccepted) {
    return (
      <div style={{
        minHeight: '100vh', background: '#f5f7fa',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '40px 16px',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 32, marginBottom: 6 }}>⚖</div>
          <h1 style={{ color: '#0a2540', fontSize: 20, fontWeight: 700, margin: 0 }}>
            Cruel &amp; Associates — Client Portal
          </h1>
          <p style={{ color: '#64748b', marginTop: 6, fontSize: 13 }}>
            Before creating your account, please review this required disclosure.
          </p>
        </div>
        <CroaDisclosure
          inline
          onAccept={() => setCroaAccepted(true)}
          onDecline={() => window.location.href = '/'}
        />
        <p style={{ marginTop: 16, fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
          Already have an account?{' '}
          <a href="/portal/login" style={{ color: '#1d4ed8' }}>Sign in</a>
        </p>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#f5f7fa',
      display: 'flex', justifyContent: 'center', padding: '40px 16px',
    }}>
      <div style={{ width: '100%', maxWidth: 560 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>⚖</div>
          <h1 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Create Your Client Account
          </h1>
          <p style={{ color: '#64748b', marginTop: 6, fontSize: 14 }}>
            Cruel &amp; Associates — Secure Client Portal
          </p>
        </div>

        <div style={{
          background: '#fff', borderRadius: 12, padding: 32,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        }}>
          {error && (
            <div style={{
              background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
              borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <SectionLabel>Personal Information</SectionLabel>
            <div style={rowStyle}>
              <Field label="First Name *" value={form.first_name} onChange={v => set('first_name', v)} required />
              <Field label="Last Name *" value={form.last_name} onChange={v => set('last_name', v)} required />
            </div>
            <Field label="Email Address *" type="email" value={form.email} onChange={v => set('email', v)} required />
            <Field label="Phone Number" type="tel" value={form.phone} onChange={v => set('phone', v)} placeholder="(555) 000-0000" />
            <Field label="Date of Birth" type="date" value={form.dob} onChange={v => set('dob', v)} />
            <Field label="Last 4 of SSN" value={form.ssn_last4} onChange={v => set('ssn_last4', v)} maxLength={4} placeholder="0000" />

            <SectionLabel style={{ marginTop: 24 }}>Address</SectionLabel>
            <Field label="Street Address" value={form.address} onChange={v => set('address', v)} placeholder="123 Main St" />
            <div style={rowStyle}>
              <Field label="City" value={form.city} onChange={v => set('city', v)} />
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>State</label>
                <select
                  value={form.state}
                  onChange={e => set('state', e.target.value)}
                  style={{ ...inputStyle, width: '100%' }}
                >
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <Field label="ZIP Code" value={form.zip_code} onChange={v => set('zip_code', v)} maxLength={10} style={{ flex: 0.8 }} />
            </div>

            <SectionLabel style={{ marginTop: 24 }}>Create Login</SectionLabel>
            <Field label="Username *" value={form.username} onChange={v => set('username', v)} required autoComplete="new-username" />
            <div style={rowStyle}>
              <Field label="Password *" type="password" value={form.password} onChange={v => set('password', v)} required autoComplete="new-password" />
              <Field label="Confirm Password *" type="password" value={form.confirm_password} onChange={v => set('confirm_password', v)} required autoComplete="new-password" />
            </div>

            <div style={{
              background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8,
              padding: '12px 14px', marginBottom: 20, fontSize: 12, color: '#0c4a6e',
              lineHeight: 1.6,
            }}>
              Your information is protected under the Gramm-Leach-Bliley Act and used solely
              for the purpose of credit dispute preparation and advocacy on your behalf.
            </div>

            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? 'Creating Account…' : 'Create Account & Access Portal'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#64748b' }}>
            Already have an account?{' '}
            <a href="/portal/login" style={{ color: '#1d4ed8', fontWeight: 600, textDecoration: 'none' }}>
              Sign in
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionLabel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
      letterSpacing: 0.8, marginBottom: 12, borderBottom: '1px solid #e2e8f0',
      paddingBottom: 6, ...style,
    }}>
      {children}
    </div>
  );
}

function Field({
  label, value, onChange, type = 'text', required = false,
  placeholder, maxLength, autoComplete, style,
}: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; required?: boolean; placeholder?: string;
  maxLength?: number; autoComplete?: string; style?: React.CSSProperties;
}) {
  return (
    <div style={{ flex: 1, marginBottom: 14, ...style }}>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        maxLength={maxLength}
        autoComplete={autoComplete}
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
      />
    </div>
  );
}

const rowStyle: React.CSSProperties = { display: 'flex', gap: 12 };
const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5,
};
const inputStyle: React.CSSProperties = {
  padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none',
};
const btnStyle: React.CSSProperties = {
  width: '100%', background: '#0a2540', color: '#fff', border: 'none',
  borderRadius: 8, padding: '13px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer',
  marginBottom: 4,
};
