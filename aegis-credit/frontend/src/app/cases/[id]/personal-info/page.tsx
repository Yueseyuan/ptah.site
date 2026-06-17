'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listPersonalInfo, analyzePersonalInfo } from '@/lib/api';

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

const SEV_COLOR: Record<string, { bg: string; text: string }> = {
  high: { bg: '#fee2e2', text: '#991b1b' },
  medium: { bg: '#fef3c7', text: '#92400e' },
  low: { bg: '#dbeafe', text: '#1e40af' },
};

function parseSafe(val: string | null | undefined): string[] {
  if (!val) return [];
  try { const p = JSON.parse(val); return Array.isArray(p) ? p : []; } catch { return []; }
}

export default function PersonalInfoPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [records, setRecords] = useState<PIRecord[]>([]);
  const [findings, setFindings] = useState<PIFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    listPersonalInfo(caseId).then(setRecords).finally(() => setLoading(false));
  }, [caseId]);

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
          <button className="btn btn-primary" onClick={analyze} disabled={analyzing || records.length === 0}>
            {analyzing ? 'Analyzing…' : '🔍 Run PI Analysis'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        <div className="disclosure-banner">
          All findings are preliminary and require human review before any action is taken. No finding constitutes a proven violation, legal advice, or a guarantee of any outcome.
        </div>

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        {loading ? (
          <p>Loading personal information records…</p>
        ) : records.length === 0 ? (
          <div className="card">
            <p style={{ color: '#6b7280' }}>No personal information records found. Upload and parse credit reports to populate this section.</p>
          </div>
        ) : (
          <>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Bureau Comparison</h2>
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
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>PI Analysis Findings</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {findings.map((f, i) => {
                const colors = SEV_COLOR[f.severity] || { bg: '#f3f4f6', text: '#374151' };
                return (
                  <div key={i} className="card" style={{ borderLeft: `4px solid ${colors.text}` }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                      <span style={{ background: '#1e40af', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, fontFamily: 'monospace' }}>{f.rule_code}</span>
                      <span style={{ background: colors.bg, color: colors.text, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600, textTransform: 'uppercase' }}>{f.severity}</span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{f.rule_name}</span>
                    </div>
                    <p style={{ margin: '0 0 6px', fontSize: 13, color: '#374151' }}>{f.description}</p>
                    {f.fcra_section && <p style={{ margin: 0, fontSize: 11, color: '#6b7280' }}>FCRA Reference: {f.fcra_section}</p>}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
