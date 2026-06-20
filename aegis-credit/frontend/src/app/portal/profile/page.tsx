'use client';
import { useEffect, useState } from 'react';
import { portalMe, portalUpdateProfile } from '@/lib/portal-api';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
];

interface ClientProfile {
  id: number; first_name: string; last_name: string; email: string;
  phone: string; address: string; city: string; state: string;
  zip_code: string; dob: string; ssn_last4: string;
}

export default function PortalProfilePage() {
  const [profile, setProfile] = useState<ClientProfile | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    portalMe().then(data => {
      setProfile(data.client);
      setForm({ ...data.client });
    }).catch(() => setError('Failed to load profile.')).finally(() => setLoading(false));
  }, []);

  function set(field: string, value: string) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSuccess('');
    setError('');
    try {
      // Only send editable fields (not email, id)
      const { email: _e, id: _id, ...editable } = form as Record<string, string>;
      void _e; void _id;
      await portalUpdateProfile(editable);
      setSuccess('Profile updated successfully.');
    } catch {
      setError('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div style={{ padding: 40, color: '#64748b', textAlign: 'center' }}>Loading…</div>;
  if (!profile) return null;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>My Profile</h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Keep your personal information up to date so we can prepare accurate dispute letters.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 28 }}>
        {success && (
          <div style={{
            background: '#f0fdf4', color: '#166534', border: '1px solid #86efac',
            borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14,
          }}>
            {success}
          </div>
        )}
        {error && (
          <div style={{
            background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
            borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14,
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Section label="Personal Information">
            <Row>
              <Field label="First Name *" value={form.first_name || ''} onChange={v => set('first_name', v)} required />
              <Field label="Last Name *" value={form.last_name || ''} onChange={v => set('last_name', v)} required />
            </Row>
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Email Address</label>
              <div style={{ ...inputStyle, background: '#f9fafb', color: '#64748b', cursor: 'default' }}>
                {profile.email}
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                Email cannot be changed. Contact your case manager to update.
              </div>
            </div>
            <Row>
              <Field label="Phone Number" type="tel" value={form.phone || ''} onChange={v => set('phone', v)} placeholder="(555) 000-0000" />
              <Field label="Date of Birth" type="date" value={form.dob || ''} onChange={v => set('dob', v)} />
            </Row>
            <Field label="Last 4 of SSN" value={form.ssn_last4 || ''} onChange={v => set('ssn_last4', v)} maxLength={4} placeholder="Used for identity verification in dispute letters" />
          </Section>

          <Section label="Mailing Address">
            <Field label="Street Address" value={form.address || ''} onChange={v => set('address', v)} placeholder="123 Main St" />
            <Row>
              <Field label="City" value={form.city || ''} onChange={v => set('city', v)} />
              <div style={{ flex: 1, marginBottom: 14 }}>
                <label style={labelStyle}>State</label>
                <select
                  value={form.state || 'SC'}
                  onChange={e => set('state', e.target.value)}
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
                >
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <Field label="ZIP Code" value={form.zip_code || ''} onChange={v => set('zip_code', v)} maxLength={10} style={{ flex: 0.8 }} />
            </Row>
          </Section>

          <div style={{ marginTop: 8 }}>
            <button type="submit" disabled={saving} style={btnStyle}>
              {saving ? 'Saving…' : 'Save Profile'}
            </button>
          </div>
        </form>
      </div>

      <div style={{
        background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 10,
        padding: '14px 18px', marginTop: 16, fontSize: 12, color: '#0c4a6e', lineHeight: 1.6,
      }}>
        <strong>Privacy Notice:</strong> Your personal information is used exclusively for
        credit dispute letters prepared on your behalf. It is protected under the
        Gramm-Leach-Bliley Act (15 U.S.C. §§6801–6802) and will never be sold or shared
        with third parties.
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
        letterSpacing: 0.8, marginBottom: 14, borderBottom: '1px solid #e2e8f0', paddingBottom: 6,
      }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', gap: 12 }}>{children}</div>;
}

function Field({
  label, value, onChange, type = 'text', required = false,
  placeholder, maxLength, style,
}: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; required?: boolean; placeholder?: string;
  maxLength?: number; style?: React.CSSProperties;
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
        style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
      />
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5,
};
const inputStyle: React.CSSProperties = {
  padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none',
  display: 'block',
};
const btnStyle: React.CSSProperties = {
  background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8,
  padding: '11px 28px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
};
