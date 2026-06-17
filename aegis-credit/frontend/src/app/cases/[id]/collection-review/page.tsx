'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listCollectionFindings, runCollectionAnalysis } from '@/lib/api';

interface CollectionFinding {
  id: number;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
  tradeline_ids?: number[];
  bureaus_affected?: string[];
}

export default function CollectionReviewPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<CollectionFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() {
    listCollectionFindings(caseId).then(data => {
      // The list endpoint returns Finding objects; the analyze endpoint returns richer objects
      // Parse rule_code from title if needed
      setFindings(data.map((f: {id: number; title?: string; description?: string; severity?: string; fcra_section?: string; rule_code?: string}) => ({
        ...f,
        rule_code: f.rule_code || (f.title || '').split(':')[0].trim(),
        rule_name: (f.title || '').split(':').slice(1).join(':').trim() || f.title || '',
      })));
    }).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [caseId]);

  async function runAnalysis() {
    setRunning(true); setError(''); setSuccess('');
    try {
      const result = await runCollectionAnalysis(caseId);
      setSuccess(`Analysis complete. ${result.findings_generated} finding(s) generated.`);
      setFindings(result.findings || []);
    } catch {
      setError('Analysis failed.');
    } finally {
      setRunning(false);
    }
  }

  const sevColor: Record<string, string> = { high: '#fee2e2', medium: '#fef3c7', low: '#dbeafe', info: '#f3f4f6' };
  const sevText: Record<string, string> = { high: '#991b1b', medium: '#92400e', low: '#1e40af', info: '#374151' };

  // Group by rule_code
  const grouped = findings.reduce((acc, f) => {
    const key = f.rule_code || 'OTHER';
    if (!acc[key]) acc[key] = [];
    acc[key].push(f);
    return acc;
  }, {} as Record<string, CollectionFinding[]>);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Collection Account Review</h1><p>Debt buyer detection, balance discrepancies, and FCRA §605 compliance</p></div>
          <button className="btn btn-primary" onClick={runAnalysis} disabled={running}>
            {running ? 'Analyzing…' : '⚡ Run Collection Analysis'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        {loading ? <div className="spinner" /> : findings.length === 0 ? (
          <div className="card">
            <p className="empty">No collection findings. Click &apos;Run Collection Analysis&apos; to check for debt buyer accounts.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([ruleCode, group]) => (
            <div key={ruleCode} className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 12, color: 'var(--navy)' }}>{ruleCode}</h3>
              {group.map(f => (
                <div key={f.id} style={{ marginBottom: 12, padding: '12px 16px', background: 'var(--bg)', borderRadius: 6, borderLeft: `4px solid ${f.severity === 'high' ? 'var(--danger)' : f.severity === 'medium' ? 'var(--warning)' : 'var(--info)'}` }}>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                    <span style={{ background: sevColor[f.severity] || '#f3f4f6', color: sevText[f.severity] || '#374151', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>{(f.severity || 'info').toUpperCase()}</span>
                    {f.fcra_section && <code style={{ fontSize: 11 }}>{f.fcra_section}</code>}
                  </div>
                  <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 6 }}>{f.description}</p>
                  <div className="review-flag">Human Review Required</div>
                  {f.bureaus_affected && f.bureaus_affected.length > 0 && (
                    <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>Bureaus: {f.bureaus_affected.join(', ')}</p>
                  )}
                </div>
              ))}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
