'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listAppointments, createAppointment, updateAppointment } from '@/lib/api';

const TYPES = ['consultation', 'notary', 'follow_up', 'signing', 'other'];

export default function AppointmentsPage() {
  const [appts, setAppts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ client_id: '', title: '', appointment_type: 'consultation', scheduled_at: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try { setAppts(await listAppointments()); } finally { setLoading(false); }
  }

  function set(k: string, v: string) { setForm((f) => ({ ...f, [k]: v })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await createAppointment({ ...form, client_id: Number(form.client_id) });
      setShowForm(false);
      setForm({ client_id: '', title: '', appointment_type: 'consultation', scheduled_at: '', notes: '' });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create appointment.');
    } finally { setSaving(false); }
  }

  async function cancel(id: number) {
    await updateAppointment(id, { status: 'cancelled' });
    await load();
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Appointments</h1><p>Schedule and manage client appointments</p></div>
          <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
            {showForm ? 'Cancel' : '+ New Appointment'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 16, fontSize: 15 }}>New Appointment</h3>
            <form onSubmit={handleSubmit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Client ID *</label>
                  <input type="number" value={form.client_id} onChange={(e) => set('client_id', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Title *</label>
                  <input value={form.title} onChange={(e) => set('title', e.target.value)} required />
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label>Type</label>
                  <select value={form.appointment_type} onChange={(e) => set('appointment_type', e.target.value)}>
                    {TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Date & Time *</label>
                  <input type="datetime-local" value={form.scheduled_at} onChange={(e) => set('scheduled_at', e.target.value)} required />
                </div>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea rows={2} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
              </div>
              {error && <p className="error-msg" style={{ marginBottom: 8 }}>{error}</p>}
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Create Appointment'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? <div className="spinner" /> : appts.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>No appointments scheduled.</p>
          ) : (
            <table>
              <thead><tr><th>Title</th><th>Client</th><th>Type</th><th>Date</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {appts.map((a: any) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>{a.title}</td>
                    <td>#{a.client_id}</td>
                    <td>{a.appointment_type?.replace('_', ' ')}</td>
                    <td style={{ fontSize: 13 }}>{new Date(a.scheduled_at).toLocaleString()}</td>
                    <td><span style={{
                      background: a.status === 'scheduled' ? '#3b82f6' : a.status === 'completed' ? '#10b981' : '#6b7280',
                      color: 'white', borderRadius: 4, padding: '2px 8px', fontSize: 11,
                    }}>{a.status}</span></td>
                    <td>
                      {a.status === 'scheduled' && (
                        <button onClick={() => cancel(a.id)} className="btn btn-outline btn-sm">Cancel</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
