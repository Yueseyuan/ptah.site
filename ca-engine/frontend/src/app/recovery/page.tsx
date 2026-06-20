'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listRecoveryCases, createRecoveryCase, listClients } from '@/lib/api';

interface RecoveryCase {
  id: number;
  case_number: string;
  client_id: number;
  case_type: string;
  status: string;
  subject_name: string;
  subject_ssn_last4: string;
  claimant_relationship: string;
  total_found: number;
  total_recovered: number;
  created_at: string;
}

interface Client { id: number; first_name: string; last_name: string; }

const CASE_TYPES = ['unclaimed_funds', 'judgment_enforcement', 'estate_asset', 'insurance_claim'];
const ALL_STATES = ['SC', 'NC', 'GA', 'FL', 'TN', 'VA', 'TX', 'NY'];

const blank = {
  client_id: '', case_type: 'unclaimed_funds', subject_name: '',
  subject_ssn_last4: '', subject_dob: '', claimant_relationship: 'self', notes: '',
};

export default function RecoveryPage() {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState<Record<string, string>>(blank);
  const [states, setStates] = useState<string[]>(ALL_STATES);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function load() {
    try {
      const [r, c] = await Promise.all([listRecoveryCases(), listClients()]);
      setCases(r);
      setClients(c);
    } catch { /* backend offline */ }
  }

  useEffect(() => { load(); }, []);

  function toggleState(s: string) {
    setStates(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr('');
    try {
      const payload: Record<string, unknown> = {
        client_id: Number(form.client_id),
        case_type: form.case_type,
        subject_name: form.subject_name,
        claimant_relationship: form.claimant_relationship,
        states_searched: states,
      };
      if (form.subject_ssn_last4) payload.subject_ssn_last4 = form.subject_ssn_last4;
      if (form.subject_dob) payload.subject_dob = form.subject_dob;
      if (form.notes) payload.notes = form.notes;
      await createRecoveryCase(payload);
      setForm(blank);
      setStates(ALL_STATES);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      setErr(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message || 'Failed to create case.');
    } finally {
      setSaving(false);
    }
  }

  const clientName = (id: number) => {
    const c = clients.find(c => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : `#${id}`;
  };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Division 5 — Asset Recovery</h1>
            <p>
              30% contingency — billed ONLY after funds received by client. SC §27-18-190: written agreement before services begin.
              8-state search: SC, NC, GA, FL, TN, VA, TX, NY.
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Cancel' : '+ New Case'}
          </button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ color: 'var(--navy)', marginBottom: 8 }}>Open Recovery Case</h3>
            <div className="disclosure-banner" style={{ marginBottom: 16 }}>
              Contingency fee agreement must be signed in writing BEFORE services begin (SC §27-18-190).
            </div>
            {err && <div className="alert-error">{err}</div>}
            <form onSubmit={submit}>
              <div className="grid-2">
                <div className="form-group">
                  <label>Client *</label>
                  <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                    <option value="">Select client…</option>
                    {clients.map(c => <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Case Type *</label>
                  <select value={form.case_type} onChange={e => setForm(f => ({ ...f, case_type: e.target.value }))}>
                    {CASE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Subject Name *</label>
                  <input value={form.subject_name} onChange={e => setForm(f => ({ ...f, subject_name: e.target.value }))} required />
                </div>
                <div className="form-group">
                  <label>Claimant Relationship *</label>
                  <select value={form.claimant_relationship} onChange={e => setForm(f => ({ ...f, claimant_relationship: e.target.value }))}>
                    <option value="self">Self</option>
                    <option value="heir">Heir</option>
                    <option value="spouse">Spouse</option>
                    <option value="estate_rep">Estate Rep</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Subject SSN (last 4 only)</label>
                  <input maxLength={4} value={form.subject_ssn_last4}
                    onChange={e => setForm(f => ({ ...f, subject_ssn_last4: e.target.value.replace(/\D/g, '').slice(0, 4) }))} />
                </div>
                <div className="form-group">
                  <label>Subject DOB</label>
                  <input type="date" value={form.subject_dob} onChange={e => setForm(f => ({ ...f, subject_dob: e.target.value }))} />
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>States to Search</label>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 6 }}>
                    {ALL_STATES.map(s => (
                      <label key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontWeight: 400, color: 'var(--text)' }}>
                        <input type="checkbox" checked={states.includes(s)} onChange={() => toggleState(s)} style={{ width: 'auto' }} />
                        {s}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Notes</label>
                  <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Opening…' : 'Open Case'}
              </button>
            </form>
          </div>
        )}

        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Case #</th>
                <th>Client</th>
                <th>Type</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Found</th>
                <th>Recovered</th>
                <th>Fee (30%)</th>
                <th>Opened</th>
              </tr>
            </thead>
            <tbody>
              {cases.length === 0 && (
                <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>No recovery cases yet.</td></tr>
              )}
              {cases.map(c => (
                <tr key={c.id}>
                  <td><code>{c.case_number}</code></td>
                  <td>{clientName(c.client_id)}</td>
                  <td>{c.case_type.replace(/_/g, ' ')}</td>
                  <td>{c.subject_name}{c.subject_ssn_last4 ? ` (xxxx-${c.subject_ssn_last4})` : ''}</td>
                  <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                  <td>${(c.total_found ?? 0).toFixed(2)}</td>
                  <td>${(c.total_recovered ?? 0).toFixed(2)}</td>
                  <td>${((c.total_recovered ?? 0) * 0.3).toFixed(2)}</td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
