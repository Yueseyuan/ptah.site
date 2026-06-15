'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listComparisons, runComparison } from '@/lib/api';

interface Comparison { id: number; creditor_name: string; account_number_last4: string; discrepancy_type: string; bureaus_affected: string[]; details: string; severity: string; }

export default function ComparisonPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() { listComparisons(caseId).then(setComparisons).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function run() {
    setRunning(true); setError(''); setSuccess('');
    try {
      const result = await runComparison(caseId);
      setSuccess(`Found ${result.comparisons_found} discrepancies.`);
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Comparison failed.');
    } finally { setRunning(false); }
  }

  const sevColor: Record<string, string> = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--info)' };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Cross-Bureau Comparison</h1><p>Detect discrepancies between Experian, Equifax, TransUnion, and Innovis</p></div>
          <button className="btn btn-primary" onClick={run} disabled={running}>{running ? 'Running…' : 'Run Comparison'}</button>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        <div className="disclosure-banner">
          All discrepancies are preliminary findings for investigator review. No discrepancy constitutes a proven FCRA violation. Human review required before any action.
        </div>

        <div className="card">
          <h3>Discrepancies Found ({comparisons.length})</h3>
          {loading ? <div className="spinner" /> : comparisons.length === 0 ? (
            <p className="empty">No comparisons yet. Click "Run Comparison" to analyze tradelines across bureaus.</p>
          ) : (
            <table>
              <thead><tr><th>Severity</th><th>Creditor</th><th>Account</th><th>Type</th><th>Bureaus Affected</th><th>Details</th></tr></thead>
              <tbody>
                {comparisons.map(c => (
                  <tr key={c.id}>
                    <td><span style={{ color: sevColor[c.severity], fontWeight: 700, fontSize: 12 }}>{c.severity.toUpperCase()}</span></td>
                    <td style={{ fontWeight: 600 }}>{c.creditor_name}</td>
                    <td><code>xxxx-{c.account_number_last4}</code></td>
                    <td><span className="badge badge-pending">{c.discrepancy_type}</span></td>
                    <td>{c.bureaus_affected.join(', ')}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)', maxWidth: 300 }}>{c.details}</td>
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
