'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { createClient } from '@/lib/api';

export default function NewClientPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    address: '', city: '', state: 'SC', zip_code: '', dob: '', ssn_last4: '', notes: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function f(k: string, v: string) { setForm(p => ({ ...p, [k]: v })); }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const client = await createClient(form);
      router.push(`/clients/${client.id}`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : d ? JSON.stringify(d) : e.message || 'Failed to create client.');
    } finally { setLoading(false); }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header"><h1>New Client</h1><p>Add a new client to Aegis</p></div>
        <form onSubmit={submit} style={{ maxWidth: 680 }}>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Personal Information</h3>
            <div className="grid-2">
              <div className="form-group"><label>First Name *</label><input required value={form.first_name} onChange={e => f('first_name', e.target.value)} /></div>
              <div className="form-group"><label>Last Name *</label><input required value={form.last_name} onChange={e => f('last_name', e.target.value)} /></div>
              <div className="form-group"><label>Email</label><input type="email" value={form.email} onChange={e => f('email', e.target.value)} /></div>
              <div className="form-group"><label>Phone</label><input value={form.phone} onChange={e => f('phone', e.target.value)} /></div>
              <div className="form-group"><label>Date of Birth</label><input type="date" value={form.dob} onChange={e => f('dob', e.target.value)} /></div>
              <div className="form-group"><label>SSN (last 4 only)</label><input maxLength={4} value={form.ssn_last4} onChange={e => f('ssn_last4', e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="xxxx" /></div>
            </div>
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Address</h3>
            <div className="form-group"><label>Street Address</label><input value={form.address} onChange={e => f('address', e.target.value)} /></div>
            <div className="grid-2">
              <div className="form-group"><label>City</label><input value={form.city} onChange={e => f('city', e.target.value)} /></div>
              <div className="form-group"><label>State</label><input value={form.state} onChange={e => f('state', e.target.value)} /></div>
              <div className="form-group"><label>ZIP</label><input value={form.zip_code} onChange={e => f('zip_code', e.target.value)} /></div>
            </div>
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Notes</h3>
            <div className="form-group"><textarea rows={3} value={form.notes} onChange={e => f('notes', e.target.value)} placeholder="Internal notes…" /></div>
          </div>
          {error && <div className="alert-error">{error}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Saving…' : 'Create Client'}</button>
            <button type="button" className="btn btn-outline" onClick={() => router.back()}>Cancel</button>
          </div>
        </form>
      </main>
    </div>
  );
}
