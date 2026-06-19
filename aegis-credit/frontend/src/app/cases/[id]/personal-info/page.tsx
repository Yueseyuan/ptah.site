'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listPersonalInfo, createPersonalInfo, deletePersonalInfo, analyzePersonalInfo, listDisputeRoundsForCase, addFindingToDispute } from '@/lib/api';

interface PIRecord {
  id: number;
  bureau: string;
  current_name: string;
  aliases: string;
  current_address: string;
  previous_addresses: string;
  current_employer: string;
  previous_employers: string;
  phone_numbers: string;
  dob: string;
  ssn_last4: string;
}

interface PIFinding {
  id?: number;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
}

interface DisputeRound {
  id: number;
  round_number: number;
  bureau: string | null;
  recipient_name: string | null;
  status: string;
}

const SEV_COLOR: Record<string, { bg: string; text: string }> = {
  high: { bg: '#fee2e2', text: '#991b1b' },
  medium: { bg: '#fef3c7', text: '#92400e' },
  low: { bg: '#dbeafe', text: '#1e40af' },
};

function parseSafe(val: string | null | undefined): string[] {
  if (!val) return [];
  try { const p = JSON.parse(val); return Array.isArray(p) ? p : []; } catch { return []; }
}

function PIFindingCard({
  f,
  rounds,
}: {
  f: PIFinding;
  rounds: DisputeRound[];
}) {
  const [expanded, setExpanded] = useState(false);
  const [selectedRound, setSelectedRound] = useState<number | ''>('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState('');

  const colors = SEV_COLOR[f.severity] || { bg: '#f3f4f6', text: '#374151' };

  async function handleAdd() {
    if (!selectedRound || !f.id) return;
    setSubmitting(true); setErr('');
    try {
      await addFindingToDispute(f.id, selectedRound as number, f.description, f.fcra_section);
      setDone(true);
      setExpanded(false);
    } catch {
      setErr('Failed to add to dispute.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ borderLeft: `4px solid ${colors.text}` }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ background: '#1e40af', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, fontFamily: 'monospace' }}>{f.rule_code}</span>
          <span style={{ background: colors.bg, color: colors.text, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' }}>{f.severity}</span>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{f.rule_name}</span>
        </div>
        {f.id && (
          done ? (
            <span style={{ fontSize: 11, background: '#d1fae5', color: '#065f46', borderRadius: 4, padding: '2px 8px', fontWeight: 600 }}>✓ Added to dispute</span>
          ) : rounds.length > 0 ? (
            <button
              onClick={() => setExpanded(s => !s)}
              style={{ fontSize: 11, background: expanded ? '#e0e7ff' : '#f0fdf4', color: expanded ? '#3730a3' : '#166534', border: '1px solid currentColor', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontWeight: 600 }}>
              {expanded ? 'Cancel' : '+ Dispute'}
            </button>
          ) : null
        )}
      </div>
      <p style={{ margin: '0 0 6px', fontSize: 13, color: '#374151' }}>{f.description}</p>
      {f.fcra_section && <p style={{ margin: 0, fontSize: 11, color: '#6b7280' }}>FCRA Reference: {f.fcra_section}</p>}

      {expanded && (
        <div style={{ marginTop: 10, padding: '10px 12px', background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>Dispute Round *</label>
          <select
            value={selectedRound}
            onChange={e => setSelectedRound(e.target.value ? parseInt(e.target.value) : '')}
            style={{ width: '100%', fontSize: 13, padding: '4px 8px', borderRadius: 4, border: '1px solid #d1d5db', marginBottom: 8 }}>
            <option value="">— select a round —</option>
            {rounds.map(r => (
              <option key={r.id} value={r.id}>
                Round #{r.round_number}{r.bureau ? ` · ${r.bureau}` : ''}{r.recipient_name ? ` — ${r.recipient_name}` : ''} ({r.status})
              </option>
            ))}
          </select>
          {err && <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 6 }}>{err}</div>}
          <button onClick={handleAdd} disabled={!selectedRound || submitting} className="btn btn-primary btn-sm">
            {submitting ? 'Adding…' : 'Add to Dispute Round'}
          </button>
        </div>
      )}
    </div>
  );
}

export default function PersonalInfoPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [records, setRecords] = useState<PIRecord[]>([]);
  const [findings, setFindings] = useState<PIFinding[]>([]);
  const [disputeRounds, setDisputeRounds] = useState<DisputeRound[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [piForm, setPiForm] = useState({ bureau: 'experian', current_name: '', aliases: '', current_address: '', previous_addresses: '', current_employer: '', previous_employers: '', phone_numbers: '', dob: '', ssn_last4: '' });
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() {
    listPersonalInfo(caseId).then(setRecords).finally(() => setLoading(false));
    listDisputeRoundsForCase(caseId).then(setDisputeRounds).catch(() => {});
  }
  useEffect(() => { load(); }, [caseId]);

  async function addRecord(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true); setError('');
    try {
      const bureausToCreate = piForm.bureau === 'all'
        ? ['experian', 'equifax', 'transunion', 'innovis']
        : [piForm.bureau];
      for (const b of bureausToCreate) {
        await createPersonalInfo({ ...piForm, bureau: b, case_id: caseId });
      }
      setShowForm(false);
      setPiForm({ bureau: 'experian', current_name: '', aliases: '', current_address: '', previous_addresses: '', current_employer: '', previous_employers: '', phone_numbers: '', dob: '', ssn_last4: '' });
      load();
    } catch { setError('Failed to add record.'); }
    finally { setAdding(false); }
  }

  async function removeRecord(rid: number) {
    await deletePersonalInfo(rid);
    load();
  }

  async function analyze() {
    setAnalyzing(true); setError(''); setSuccess('');
    try {
      const r = await analyzePersonalInfo(caseId);
      setFindings(r.findings || []);
      setSuccess(`Analysis complete: ${r.findings_generated} finding(s) generated from ${r.records_analyzed} record(s).`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Analysis failed.');
    } finally { setAnalyzing(false); }
  }

  const bureaus = Array.from(new Set(records.map(r => r.bureau))).sort();

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Personal Information Audit</h1>
            <p>Cross-bureau comparison of consumer personal information records</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-outline" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Record'}</button>
            <button className="btn btn-primary" onClick={analyze} disabled={analyzing || records.length === 0}>
              {analyzing ? 'Analyzing…' : '🔍 Run PI Analysis'}
            </button>
          </div>
        </div>
        <CaseNav caseId={caseId} />

        <div className="disclosure-banner">
          All findings are preliminary and require human review before any action is taken. No finding constitutes a proven violation, legal advice, or a guarantee of any outcome.
        </div>

        {error && <div className="alert-error" style={{ marginBottom: 12 }}>{error}</div>}
        {success && <div className="alert-success" style={{ marginBottom: 12 }}>{success}</div>}

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add PI Record</h3>
            <form onSubmit={addRecord}>
              <div className="grid-2">
                <div className="form-group"><label>Bureau *</label>
                  <select value={piForm.bureau} onChange={e => setPiForm(f => ({ ...f, bureau: e.target.value }))}>
                    <option value="all">All Bureaus</option>
                    {['experian','equifax','transunion','innovis'].map(b => <option key={b} value={b}>{b}</option>)}
                  </select>
                </div>
                <div className="form-group"><label>Name on Report *</label><input required value={piForm.current_name} onChange={e => setPiForm(f => ({ ...f, current_name: e.target.value }))} /></div>
                <div className="form-group"><label>Aliases / Also Known As</label><input value={piForm.aliases} onChange={e => setPiForm(f => ({ ...f, aliases: e.target.value }))} placeholder="e.g. Randy Sullivan, R Sullivan" /></div>
                <div className="form-group"><label>Current Address</label><input value={piForm.current_address} onChange={e => setPiForm(f => ({ ...f, current_address: e.target.value }))} /></div>
                <div className="form-group"><label>Previous Addresses</label><input value={piForm.previous_addresses} onChange={e => setPiForm(f => ({ ...f, previous_addresses: e.target.value }))} placeholder="Separate multiple with semicolon" /></div>
                <div className="form-group"><label>Date of Birth</label><input type="date" value={piForm.dob} onChange={e => setPiForm(f => ({ ...f, dob: e.target.value }))} /></div>
                <div className="form-group"><label>SSN Last 4</label><input maxLength={4} value={piForm.ssn_last4} onChange={e => setPiForm(f => ({ ...f, ssn_last4: e.target.value.replace(/\D/g,'').slice(0,4) }))} placeholder="xxxx" /></div>
                <div className="form-group"><label>Current Employer</label><input value={piForm.current_employer} onChange={e => setPiForm(f => ({ ...f, current_employer: e.target.value }))} /></div>
                <div className="form-group"><label>Previous Employers</label><input value={piForm.previous_employers} onChange={e => setPiForm(f => ({ ...f, previous_employers: e.target.value }))} placeholder="Separate multiple with semicolon" /></div>
                <div className="form-group"><label>Phone Numbers</label><input value={piForm.phone_numbers} onChange={e => setPiForm(f => ({ ...f, phone_numbers: e.target.value }))} placeholder="Separate multiple with semicolon" /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm" disabled={adding}>{adding ? 'Saving…' : 'Save Record'}</button>
            </form>
          </div>
        )}

        {loading ? (
          <p>Loading personal information records…</p>
        ) : records.length === 0 ? (
          <div className="card">
            <p style={{ color: '#6b7280' }}>No personal information records found. Upload and parse credit reports to populate this section.</p>
          </div>
        ) : (
          <>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Bureau Records
            <span style={{ marginLeft: 8, fontSize: 12, fontWeight: 400, color: 'var(--muted)' }}>{records.length} record{records.length !== 1 ? 's' : ''} · <button onClick={() => records.forEach(r => removeRecord(r.id))} style={{ background:'none',border:'none',color:'#ef4444',cursor:'pointer',fontSize:12,padding:0 }}>clear all</button></span>
          </h2>
            <div style={{ overflowX: 'auto', marginBottom: 24 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9fafb' }}>
                    <th style={{ padding: '8px 12px', textAlign: 'left', borderBottom: '2px solid #e5e7eb', fontWeight: 600 }}>Field</th>
                    {bureaus.map(b => (
                      <th key={b} style={{ padding: '8px 12px', textAlign: 'left', borderBottom: '2px solid #e5e7eb', fontWeight: 600, textTransform: 'capitalize' }}>{b}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { key: 'current_name', label: 'Current Name' },
                    { key: 'aliases', label: 'Aliases', array: true },
                    { key: 'current_address', label: 'Current Address' },
                    { key: 'previous_addresses', label: 'Previous Addresses', array: true },
                    { key: 'current_employer', label: 'Current Employer' },
                    { key: 'previous_employers', label: 'Previous Employers', array: true },
                    { key: 'phone_numbers', label: 'Phone Numbers', array: true },
                    { key: 'dob', label: 'Date of Birth' },
                    { key: 'ssn_last4', label: 'SSN Last 4' },
                  ].map(({ key, label, array }) => (
                    <tr key={key} style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <td style={{ padding: '8px 12px', fontWeight: 500, color: '#374151', whiteSpace: 'nowrap' }}>{label}</td>
                      {bureaus.map(b => {
                        const rec = records.find(r => r.bureau === b);
                        const val = rec ? (rec as unknown as Record<string, string>)[key] : null;
                        const display = array ? parseSafe(val).join(', ') || '—' : (val || '—');
                        return (
                          <td key={b} style={{ padding: '8px 12px', color: '#374151', verticalAlign: 'top' }}>{display}</td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {findings.length > 0 && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>PI Analysis Findings</h2>
              {disputeRounds.length === 0 && (
                <span style={{ fontSize: 12, color: '#6b7280' }}>
                  Create a <a href={`/cases/${caseId}/disputes`} style={{ color: '#1e40af' }}>dispute round</a> to add findings to disputes
                </span>
              )}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {findings.map((f, i) => (
                <PIFindingCard key={f.id ?? i} f={f} rounds={disputeRounds} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
