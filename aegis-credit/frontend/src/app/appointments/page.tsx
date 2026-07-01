'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import {
  listAppointments, listUpcomingAppointments, listClients,
  createAppointment, updateAppointment, deleteAppointment,
} from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Client { id: number; first_name: string; last_name: string; }

interface Appointment {
  id: number;
  client_id: number;
  client_name?: string;
  division: string;
  type: string;
  date_time: string;
  location: string;
  duration: number;
  notes: string;
  status: string;
}

interface ApptForm {
  client_id: string;
  division: string;
  type: string;
  date_time: string;
  location: string;
  duration: string;
  notes: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DIVISIONS = ['Credit Repair', 'Debt Settlement', 'Legal', 'Consulting', 'Collections', 'Other'];
const TYPES = ['In-Person', 'Phone Call', 'Video Call', 'Email Follow-Up', 'Court Appearance', 'Other'];

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  scheduled: { bg: '#dbeafe', color: '#1e40af' },
  confirmed:  { bg: '#d1fae5', color: '#065f46' },
  completed:  { bg: '#f3f4f6', color: '#374151' },
  cancelled:  { bg: '#fee2e2', color: '#991b1b' },
};

const EMPTY_FORM: ApptForm = {
  client_id: '', division: '', type: '', date_time: '', location: '', duration: '60', notes: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDateTime(dt: string) {
  if (!dt) return '—';
  try {
    return new Date(dt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch { return dt; }
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] || { bg: '#f3f4f6', color: '#374151' };
  return (
    <span style={{
      background: s.bg, color: s.color, borderRadius: 4,
      padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
    }}>
      {status}
    </span>
  );
}

// ─── Modal wrapper ────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: 'white', borderRadius: 'var(--radius)', width: 620, maxWidth: '95vw', maxHeight: '90vh', overflowY: 'auto', padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--navy)' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--muted)', lineHeight: 1 }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [clientMap, setClientMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'list' | 'upcoming'>('list');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<ApptForm>(EMPTY_FORM);
  const [clientSearch, setClientSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  function fetchAppointments() {
    setLoading(true);
    const fetchFn = view === 'upcoming' ? listUpcomingAppointments : listAppointments;
    Promise.all([fetchFn(), listClients()])
      .then(([appts, cls]) => {
        setAppointments(appts);
        const m: Record<number, string> = {};
        for (const c of cls) m[c.id] = `${c.first_name} ${c.last_name}`;
        setClientMap(m);
        setClients(cls);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => { fetchAppointments(); }, [view]); // eslint-disable-line react-hooks/exhaustive-deps

  // Filtered client list for modal search
  const filteredClients = clientSearch.trim()
    ? clients.filter(c =>
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(clientSearch.toLowerCase())
      ).slice(0, 8)
    : clients.slice(0, 8);

  function openModal() {
    setForm(EMPTY_FORM);
    setClientSearch('');
    setFormError('');
    setShowModal(true);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.client_id) { setFormError('Please select a client.'); return; }
    setSaving(true);
    setFormError('');
    try {
      await createAppointment({
        ...form,
        client_id: parseInt(form.client_id),
        duration: parseInt(form.duration) || 60,
      });
      setSuccess('Appointment created successfully.');
      setShowModal(false);
      fetchAppointments();
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setFormError(e.response?.data?.detail || 'Failed to create appointment.');
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(id: number, status: string) {
    try {
      await updateAppointment(id, { status });
      setAppointments(prev => prev.map(a => a.id === id ? { ...a, status } : a));
    } catch {
      // keep UI consistent on failure
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Cancel and remove this appointment?')) return;
    try {
      await deleteAppointment(id);
      setAppointments(prev => prev.filter(a => a.id !== id));
    } catch {
      alert('Failed to delete appointment.');
    }
  }

  const field = (k: keyof ApptForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(prev => ({ ...prev, [k]: e.target.value }));

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">

        {/* Header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Appointments</h1>
            <p>
              {appointments.length} appointment{appointments.length !== 1 ? 's' : ''}
              {view === 'upcoming' ? ' in the next 7 days' : ''}
            </p>
          </div>
          <button className="btn btn-primary" onClick={openModal}>+ New Appointment</button>
        </div>

        {success && <div className="alert alert-success">{success}</div>}

        {/* View toggle */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button
            className={view === 'list' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}
            onClick={() => setView('list')}>
            List
          </button>
          <button
            className={view === 'upcoming' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}
            onClick={() => setView('upcoming')}>
            Upcoming (next 7 days)
          </button>
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="spinner" />
          ) : appointments.length === 0 ? (
            <p className="empty">
              {view === 'upcoming'
                ? 'No appointments scheduled in the next 7 days.'
                : 'No appointments found. Create one to get started.'}
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Division</th>
                  <th>Type</th>
                  <th>Date / Time</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map(a => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>
                      {a.client_name || clientMap[a.client_id] || `Client #${a.client_id}`}
                    </td>
                    <td style={{ color: 'var(--muted)' }}>{a.division || '—'}</td>
                    <td>{a.type || '—'}</td>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>{fmtDateTime(a.date_time)}</td>
                    <td style={{ color: 'var(--muted)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.location || '—'}
                    </td>
                    <td><StatusBadge status={a.status} /></td>
                    <td>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {a.status === 'scheduled' && (
                          <button className="btn btn-outline btn-sm" onClick={() => handleStatusChange(a.id, 'confirmed')}>
                            Confirm
                          </button>
                        )}
                        {(a.status === 'scheduled' || a.status === 'confirmed') && (
                          <button className="btn btn-outline btn-sm" onClick={() => handleStatusChange(a.id, 'completed')}>
                            Complete
                          </button>
                        )}
                        {a.status !== 'cancelled' && a.status !== 'completed' && (
                          <button
                            onClick={() => handleDelete(a.id)}
                            style={{ padding: '4px 10px', fontSize: 12, background: '#fee2e2', color: '#991b1b', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Create Modal */}
        {showModal && (
          <Modal title="New Appointment" onClose={() => setShowModal(false)}>
            {formError && <div className="alert alert-error">{formError}</div>}
            <form onSubmit={handleCreate}>

              {/* Client search / select */}
              <div className="form-group" style={{ position: 'relative' }}>
                <label>Client *</label>
                <input
                  type="text"
                  placeholder="Search client by name…"
                  value={clientSearch}
                  autoComplete="off"
                  onChange={e => {
                    setClientSearch(e.target.value);
                    setForm(p => ({ ...p, client_id: '' }));
                  }}
                />
                {clientSearch && !form.client_id && (
                  <div style={{
                    border: '1px solid var(--border)', borderRadius: 6, marginTop: 4,
                    background: 'white', maxHeight: 200, overflowY: 'auto',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  }}>
                    {filteredClients.length === 0 ? (
                      <div style={{ padding: '8px 12px', color: 'var(--muted)', fontSize: 13 }}>No clients found.</div>
                    ) : filteredClients.map(c => (
                      <div key={c.id}
                        onClick={() => {
                          setForm(p => ({ ...p, client_id: String(c.id) }));
                          setClientSearch(`${c.first_name} ${c.last_name}`);
                        }}
                        style={{ padding: '8px 12px', cursor: 'pointer', fontSize: 13, borderBottom: '1px solid var(--border)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = '#f5f6fa')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'white')}>
                        {c.first_name} {c.last_name}
                      </div>
                    ))}
                  </div>
                )}
                {form.client_id && (
                  <div style={{ fontSize: 12, color: 'var(--success)', marginTop: 4 }}>
                    Client selected (ID: {form.client_id})
                  </div>
                )}
              </div>

              <div className="grid-2">
                <div className="form-group">
                  <label>Division *</label>
                  <select required value={form.division} onChange={field('division')}>
                    <option value="">— Select division —</option>
                    {DIVISIONS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Type *</label>
                  <select required value={form.type} onChange={field('type')}>
                    <option value="">— Select type —</option>
                    {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Date &amp; Time *</label>
                  <input required type="datetime-local" value={form.date_time} onChange={field('date_time')} />
                </div>
                <div className="form-group">
                  <label>Duration (minutes)</label>
                  <input type="number" min="5" step="5" value={form.duration} onChange={field('duration')} />
                </div>
              </div>

              <div className="form-group">
                <label>Location</label>
                <input
                  type="text"
                  placeholder="Office address, Zoom link, phone number…"
                  value={form.location}
                  onChange={field('location')}
                />
              </div>

              <div className="form-group">
                <label>Notes</label>
                <textarea
                  rows={3}
                  value={form.notes}
                  onChange={field('notes')}
                  placeholder="Additional notes for this appointment…"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Creating…' : 'Create Appointment'}
                </button>
              </div>
            </form>
          </Modal>
        )}

      </main>
    </div>
  );
}
