'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { runMetro2Analysis, listMetro2Findings, listDisputeRoundsForCase, metro2FindingToDispute } from '@/lib/api';

interface Metro2Finding {
  id: number;
  case_id: number;
  tradeline_id: number | null;
  rule_code: string;
  rule_name: string;
  severity: string;
  description: string;
  fcra_section: string;
  created_at: string;
}

interface DisputeRound {
  id: number;
  round_number: number;
  bureau: string | null;
  recipient_name: string | null;
  status: string;
}

const SEVERITY_ORDER = ['high', 'medium', 'low', 'info'];
const SEVERITY_BADGE: Record<string, string> = {
  high: 'badge-high', medium: 'badge-medium', low: 'badge-low', info: 'badge-pending',
};
const SEVERITY_BORDER: Record<string, string> = {
  high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--muted)', info: 'var(--border)',
};

const RULE_CATEGORIES: Record<string, string[]> = {
  'DOFD / Obsolescence (FCRA §605)': ['DOFD_7YR', 'DOFD_APPROACHING', 'MISSING_DOFD', 'DOFD_FUTURE', 'DOFD_AFTER_REPORTED', 'DOFD_BEFORE_OPEN'],
  'Balance & Payment Fields': ['BALANCE_EXCEEDS_HIGH', 'PAST_DUE_ON_CURRENT', 'ZERO_PAST_DUE_ON_DEROGATORY', 'PAST_DUE_NOT_DEROGATORY', 'CREDIT_LIMIT_MISSING'],
  'Account Status & Reporting': ['STALE_REPORTING', 'PAYMENT_RATING_MISMATCH', 'INVALID_PAYMENT_RATING', 'OPEN_WITH_CLOSE_DATE', 'DATE_REPORTED_FUTURE'],
  'Metro 2 Code Validation': ['INVALID_COMPLIANCE_CODE', 'INVALID_CONSUMER_INFO', 'COLLECTION_MISSING_XO', 'DISPUTE_NO_XF'],
  'Bankruptcy (FCRA §605(a)(1))': ['DISCHARGED_BALANCE', 'BANKRUPTCY_10YR'],
  'FDCPA / Collection Issues': ['CHARGEOFF_GROWING_BALANCE', 'COLLECTION_EXCESSIVE_BALANCE', 'PAID_COLLECTION_NONZERO', 'SETTLED_FULL_BALANCE'],
  'Cross-Bureau Inconsistencies': ['CROSS_STATUS_MISMATCH', 'CROSS_BALANCE_MISMATCH', 'CROSS_DOFD_MISMATCH', 'CROSS_DEROGATORY_MISMATCH', 'POTENTIAL_DUPLICATE_DEBT', 'SELECTIVE_BUREAU_REPORTING'],
};

function getRuleCategory(code: string): string {
  for (const [cat, codes] of Object.entries(RULE_CATEGORIES)) {
    if (codes.includes(code)) return cat;
  }
  return 'Other';
}

function isCrossBureau(code: string): boolean {
  return code.startsWith('CROSS_') || code === 'POTENTIAL_DUPLICATE_DEBT' || code === 'SELECTIVE_BUREAU_REPORTING';
}

function FindingCard({
  f,
  rounds,
  onAddToDispute,
}: {
  f: Metro2Finding;
  rounds: DisputeRound[];
  onAddToDispute: (findingId: number, roundId: number, reason: string) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [selectedRound, setSelectedRound] = useState<number | ''>('');
  const [customReason, setCustomReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState('');

  async function handleAdd() {
    if (!selectedRound) return;
    setSubmitting(true); setErr('');
    try {
      await onAddToDispute(f.id, selectedRound as number, customReason || f.description);
      setDone(true);
      setExpanded(false);
    } catch {
      setErr('Failed to add to dispute.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: 10, borderLeft: `4px solid ${SEVERITY_BORDER[f.severity] || 'var(--border)'}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6, gap: 12 }}>
        <strong style={{ fontSize: 14 }}>{f.rule_name}</strong>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <span className={`badge ${SEVERITY_BADGE[f.severity] || 'badge-pending'}`}>{f.severity}</span>
          {isCrossBureau(f.rule_code) && (
            <span style={{ fontSize: 11, background: '#ede9fe', color: '#5b21b6', borderRadius: 4, padding: '2px 6px' }}>cross-bureau</span>
          )}
          {done ? (
            <span style={{ fontSize: 11, background: '#d1fae5', color: '#065f46', borderRadius: 4, padding: '2px 8px', fontWeight: 600 }}>✓ Added to dispute</span>
          ) : rounds.length > 0 ? (
            <button
              onClick={() => setExpanded(s => !s)}
              style={{ fontSize: 11, background: expanded ? '#e0e7ff' : '#f0fdf4', color: expanded ? '#3730a3' : '#166534', border: '1px solid currentColor', borderRadius: 4, padding: '2px 8px', cursor: 'pointer', fontWeight: 600 }}>
              {expanded ? 'Cancel' : '+ Dispute'}
            </button>
          ) : null}
        </div>
      </div>
      <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 8px 0', lineHeight: 1.5 }}>{f.description}</p>
      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--muted)', flexWrap: 'wrap' }}>
        <span>Rule: <code>{f.rule_code}</code></span>
        {f.fcra_section && <span style={{ color: 'var(--primary)', fontWeight: 500 }}>{f.fcra_section}</span>}
        {f.tradeline_id && <span>Tradeline #{f.tradeline_id}</span>}
      </div>

      {expanded && (
        <div style={{ marginTop: 12, padding: '10px 12px', background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
          <div style={{ marginBottom: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>Dispute Round *</label>
            <select
              value={selectedRound}
              onChange={e => setSelectedRound(e.target.value ? parseInt(e.target.value) : '')}
              style={{ width: '100%', fontSize: 13, padding: '4px 8px', borderRadius: 4, border: '1px solid #d1d5db' }}>
              <option value="">— select a round —</option>
              {rounds.map(r => (
                <option key={r.id} value={r.id}>
                  Round #{r.round_number}{r.bureau ? ` · ${r.bureau}` : ''}{r.recipient_name ? ` — ${r.recipient_name}` : ''} ({r.status})
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>Dispute Reason (optional — defaults to finding description)</label>
            <textarea
              value={customReason}
              onChange={e => setCustomReason(e.target.value)}
              placeholder={f.description.slice(0, 120) + '…'}
              rows={2}
              style={{ width: '100%', fontSize: 12, padding: '4px 8px', borderRadius: 4, border: '1px solid #d1d5db', resize: 'vertical', boxSizing: 'border-box' }}
            />
          </div>
          {err && <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 6 }}>{err}</div>}
          <button
            onClick={handleAdd}
            disabled={!selectedRound || submitting}
            className="btn btn-primary btn-sm">
            {submitting ? 'Adding…' : 'Add to Dispute Round'}
          </button>
        </div>
      )}
    </div>
  );
}

export default function Metro2Page() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [findings, setFindings] = useState<Metro2Finding[]>([]);
  const [disputeRounds, setDisputeRounds] = useState<DisputeRound[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<{
    tradelines_analyzed: number;
    findings_generated: number;
    severity_summary: Record<string, number>;
  } | null>(null);
  const [error, setError] = useState('');
  const [view, setView] = useState<'severity' | 'category'>('severity');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  function load() {
    Promise.all([
      listMetro2Findings(caseId),
      listDisputeRoundsForCase(caseId),
    ]).then(([f, r]) => {
      setFindings(f);
      setDisputeRounds(r);
    }).catch(() => {}).finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [caseId]);

  async function runAnalysis() {
    setRunning(true); setError('');
    try {
      const result = await runMetro2Analysis(caseId);
      setSummary({
        tradelines_analyzed: result.tradelines_analyzed,
        findings_generated: result.findings_generated,
        severity_summary: result.severity_summary,
      });
      setFindings(result.items || []);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e?.message || 'Analysis failed.');
    } finally { setRunning(false); }
  }

  async function addToDispute(metro2FindingId: number, roundId: number, reason: string) {
    await metro2FindingToDispute(metro2FindingId, roundId, reason);
    // Refresh dispute rounds in case item counts changed
    listDisputeRoundsForCase(caseId).then(setDisputeRounds).catch(() => {});
  }

  const filtered = filterSeverity === 'all' ? findings : findings.filter(f => f.severity === filterSeverity);

  const bySeverity: Record<string, Metro2Finding[]> = {};
  for (const sev of SEVERITY_ORDER) bySeverity[sev] = [];
  for (const f of filtered) {
    const key = SEVERITY_ORDER.includes(f.severity) ? f.severity : 'info';
    bySeverity[key].push(f);
  }

  const byCategory: Record<string, Metro2Finding[]> = {};
  for (const f of filtered) {
    const cat = getRuleCategory(f.rule_code);
    byCategory[cat] = byCategory[cat] || [];
    byCategory[cat].push(f);
  }

  const totalHigh = findings.filter(f => f.severity === 'high').length;
  const crossBureauCount = findings.filter(f => isCrossBureau(f.rule_code)).length;
  const obsoleteCount = findings.filter(f => ['DOFD_7YR', 'BANKRUPTCY_10YR'].includes(f.rule_code)).length;
  const reagingCount = findings.filter(f => ['DOFD_FUTURE', 'DOFD_AFTER_REPORTED', 'DOFD_BEFORE_OPEN', 'CROSS_DOFD_MISMATCH'].includes(f.rule_code)).length;
  const duplicateCount = findings.filter(f => f.rule_code === 'POTENTIAL_DUPLICATE_DEBT').length;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Metro 2 Compliance Audit</h1>
            <p>CDIA Metro 2 CRRG rules engine — FCRA §§604–625 · FDCPA §§1692a–k · 11 U.S.C. §524 · Cross-bureau consistency</p>
          </div>
          <button className="btn btn-primary" onClick={runAnalysis} disabled={running}>
            {running ? 'Analyzing…' : 'Run Full Audit'}
          </button>
        </div>
        <CaseNav caseId={caseId} />

        {error && <div className="alert-error" style={{ marginBottom: 16 }}>{error}</div>}

        <div style={{ background: '#fef9c3', border: '1px solid #ca8a04', borderRadius: 6, padding: '8px 14px', fontSize: 12, color: '#713f12', marginBottom: 16 }}>
          <strong>COMPLIANCE NOTICE:</strong> All findings are preliminary and require human review before any action.
          No finding constitutes legal advice or a guaranteed outcome.
        </div>

        {disputeRounds.length === 0 && findings.length > 0 && (
          <div style={{ background: '#eff6ff', border: '1px solid #93c5fd', borderRadius: 6, padding: '8px 14px', fontSize: 12, color: '#1e40af', marginBottom: 16 }}>
            <strong>Tip:</strong> To add findings to disputes, first create a dispute round in the <a href={`/cases/${caseId}/disputes`} style={{ color: '#1e40af', textDecoration: 'underline' }}>Disputes tab</a>.
          </div>
        )}

        {(summary || findings.length > 0) && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ marginBottom: 12 }}>Audit Summary</h3>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
              {summary && <div style={{ fontSize: 13 }}><strong>{summary.tradelines_analyzed}</strong> tradelines analyzed</div>}
              <div style={{ fontSize: 13 }}><strong>{findings.length}</strong> total findings</div>
              {totalHigh > 0 && <div><span className="badge badge-high">{totalHigh} HIGH</span></div>}
              {obsoleteCount > 0 && (
                <div style={{ fontSize: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 4, padding: '2px 8px' }}>
                  {obsoleteCount} obsolete account{obsoleteCount !== 1 ? 's' : ''} (past 7/10-yr window)
                </div>
              )}
              {reagingCount > 0 && (
                <div style={{ fontSize: 12, background: '#fef3c7', color: '#92400e', borderRadius: 4, padding: '2px 8px' }}>
                  {reagingCount} re-aging indicator{reagingCount !== 1 ? 's' : ''}
                </div>
              )}
              {crossBureauCount > 0 && (
                <div style={{ fontSize: 12, background: '#ede9fe', color: '#5b21b6', borderRadius: 4, padding: '2px 8px' }}>
                  {crossBureauCount} cross-bureau issue{crossBureauCount !== 1 ? 's' : ''}
                </div>
              )}
              {duplicateCount > 0 && (
                <div style={{ fontSize: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 4, padding: '2px 8px' }}>
                  {duplicateCount} potential duplicate debt{duplicateCount !== 1 ? 's' : ''}
                </div>
              )}
              {disputeRounds.length > 0 && (
                <div style={{ fontSize: 12, background: '#d1fae5', color: '#065f46', borderRadius: 4, padding: '2px 8px' }}>
                  {disputeRounds.length} dispute round{disputeRounds.length !== 1 ? 's' : ''} available
                </div>
              )}
            </div>
            {summary?.severity_summary && (
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {SEVERITY_ORDER.map(sev => {
                  const count = summary.severity_summary[sev] || 0;
                  if (!count) return null;
                  return (
                    <button key={sev}
                      className={`badge ${SEVERITY_BADGE[sev]}`}
                      style={{ cursor: 'pointer', outline: filterSeverity === sev ? '2px solid currentColor' : 'none', outlineOffset: 2 }}
                      onClick={() => setFilterSeverity(filterSeverity === sev ? 'all' : sev)}>
                      {sev}: {count}
                    </button>
                  );
                })}
                {filterSeverity !== 'all' && (
                  <button className="btn btn-outline btn-sm" onClick={() => setFilterSeverity('all')}>Clear filter</button>
                )}
              </div>
            )}
          </div>
        )}

        {findings.length > 0 && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button className={`btn btn-sm ${view === 'severity' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setView('severity')}>By Severity</button>
            <button className={`btn btn-sm ${view === 'category' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setView('category')}>By Category</button>
          </div>
        )}

        {loading ? <div className="spinner" /> : filtered.length === 0 ? (
          <div className="card">
            <p className="empty">
              {findings.length > 0
                ? 'No findings match the current filter.'
                : 'No Metro 2 findings yet. Click "Run Full Audit" to check all tradelines against the complete Metro 2 CRRG ruleset (26 rules covering FCRA, FDCPA, and cross-bureau consistency).'}
            </p>
          </div>
        ) : view === 'severity' ? (
          SEVERITY_ORDER.map(sev => {
            const items = bySeverity[sev];
            if (!items.length) return null;
            return (
              <div key={sev} style={{ marginBottom: 20 }}>
                <h3 style={{ textTransform: 'capitalize', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className={`badge ${SEVERITY_BADGE[sev]}`}>{sev}</span>
                  {items.length} finding{items.length !== 1 ? 's' : ''}
                </h3>
                {items.map(f => (
                  <FindingCard key={f.id} f={f} rounds={disputeRounds} onAddToDispute={addToDispute} />
                ))}
              </div>
            );
          })
        ) : (
          Object.entries(byCategory)
            .sort(([a], [b]) => {
              const catOrder = Object.keys(RULE_CATEGORIES);
              return (catOrder.indexOf(a) === -1 ? 99 : catOrder.indexOf(a)) -
                     (catOrder.indexOf(b) === -1 ? 99 : catOrder.indexOf(b));
            })
            .map(([cat, items]) => (
              <div key={cat} style={{ marginBottom: 20 }}>
                <h3 style={{ marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
                  {cat}
                  <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 400 }}>
                    — {items.length} finding{items.length !== 1 ? 's' : ''}
                  </span>
                </h3>
                {items.map(f => (
                  <FindingCard key={f.id} f={f} rounds={disputeRounds} onAddToDispute={addToDispute} />
                ))}
              </div>
            ))
        )}
      </main>
    </div>
  );
}
