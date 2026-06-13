'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { createClient } from '@/lib/api';

const SC_STATES = ['SC','AL','AR','AZ','CA','CO','CT','DC','DE','FL','GA','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'];

export default function NewClientPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    address: '', city: '', state: 'SC', zip_code: '',
    dob: '', ssn_last4: '', notes: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function set(key: string, val: string) { setForm((f) => ({ ...f, [key]: val })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!form.first_name || !form.last_name) { setError('First and last name are required.'); return; }
    if (form.ssn_last4 && (form.ssn_last4.length !== 4 || !/^\d+$/.test(form.ssn_last4))) {
      setError('SSN last 4 must be exactly 4 digits.'); return;
    }
    setLoading(true);
    try {
      const client = await createClient(form);
      router.push(`/clients/${client.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create client.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>New Client</h1>
          <p>Add a new client to the system</p>
        </div>

        <form onSubmit={handleSubmit} style={{ maxWidth: 700 }}>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Personal Information</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>First Name *</label>
                <input value={form.first_name} onChange={(e) => set('first_name', e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Last Name *</label>
                <input value={form.last_name} onChange={(e) => set('last_name', e.target.value)} required />
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} />
              </div>
              <div className="form-group">
                <label>Phone</label>
                <input type="tel" value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="(864) 000-0000" />
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Date of Birth</label>
                <input type="date" value={form.dob} onChange={(e) => set('dob', e.target.value)} />
              </div>
              <div className="form-group">
                <label>SSN Last 4 Digits</label>
                <input
                  value={form.ssn_last4}
                  onChange={(e) => set('ssn_last4', e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="XXXX"
                  maxLength={4}
                />
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>Stored as last 4 only — never full SSN</span>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Address</h3>
            <div className="form-group">
              <label>Street Address</label>
              <input value={form.address} onChange={(e) => set('address', e.target.value)} />
            </div>
            <div className="grid-3">
              <div className="form-group">
                <label>City</label>
                <input value={form.city} onChange={(e) => set('city', e.target.value)} />
              </div>
              <div className="form-group">
                <label>State</label>
                <select value={form.state} onChange={(e) => set('state', e.target.value)}>
                  {SC_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>ZIP Code</label>
                <input value={form.zip_code} onChange={(e) => set('zip_code', e.target.value)} maxLength={10} />
              </div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16 }}>Notes</h3>
            <div className="form-group">
              <textarea
                rows={4}
                value={form.notes}
                onChange={(e) => set('notes', e.target.value)}
                placeholder="Internal notes about this client…"
              />
            </div>
          </div>

          {error && <p className="error-msg" style={{ marginBottom: 12 }}>{error}</p>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create Client'}
            </button>
            <button type="button" className="btn btn-outline" onClick={() => router.back()}>Cancel</button>
          </div>
        </form>
      </main>
    </div>
  );
}
