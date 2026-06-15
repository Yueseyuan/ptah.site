'use client';
import { useEffect, useState } from 'react';
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
  states_searched: string;
  total_found: number;
  total_recovered: number;
  contingency_pct: number;
  notes: string;
  created_at: string;
}

interface Client { id: number; full_name: string; }

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
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setErr(err.response?.data?.detail || err.message || 'Failed to create case.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Division 5 — Asset Recovery</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            30% contingency — billed ONLY after funds received by client. SC §27-18-190: agreement in writing before services begin.
            8-state search: SC, NC, GA, FL, TN, VA, TX, NY.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(s => !s)}>
          {showForm ? 'Cancel' : '+ New Case'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Open Recovery Case</h3>
          {err && <div className="alert-error">{err}</div>}
          <div className="card" style={{ background: '#fff3cd', borderColor: '#ffc107', marginBottom: 16, fontSize: 13 }}>
            Contingency fee agreement must be signed in writing BEFORE services begin (SC §27-18-190).
          </div>
          <form onSubmit={submit}>
            <div className="form-grid">
              <div className="form-group">
                <label>Client *</label>
                <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">Select client…</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Case Type *</label>
                <select value={form.case_type} onChange={e => setForm(f => ({ ...f, case_type: e.target.value }))}>
                  {CASE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Subject Name *</label>
                <input value={form.subject_name} onChange={e => setForm(f => ({ ...f, subject_name: e.target.value }))} required />
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
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label>States to Search</label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                  {ALL_STATES.map(s => (
                    <label key={s} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                      <input type="checkbox" checked={states.includes(s)} onChange={() => toggleState(s)} />
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
            <div style={{ marginTop: 16 }}>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Opening…' : 'Open Case'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table className="table">
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
              <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--muted)' }}>No recovery cases yet.</td></tr>
            )}
            {cases.map(c => (
              <tr key={c.id}>
                <td><code>{c.case_number}</code></td>
                <td>{clients.find(cl => cl.id === c.client_id)?.full_name ?? `#${c.client_id}`}</td>
                <td>{c.case_type.replace('_', ' ')}</td>
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
    </div>
  );
}
