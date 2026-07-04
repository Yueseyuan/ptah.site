'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { getLatestDigest, generateDigest, getAlerts } from '@/lib/api';

interface Digest {
  id: number;
  title: string;
  content: string;
  created_at: string | null;
}

interface AlertItem {
  id: number;
  case_number: string;
  division?: string;
  status?: string;
  last_activity: string | null;
}

interface Alerts {
  generated_at: string;
  new_this_week: { credit: number; service: number };
  stale_credit: AlertItem[];
  stale_service: AlertItem[];
  at_risk: AlertItem[];
}

function MarkdownContent({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div style={{ lineHeight: 1.7, fontSize: 14 }}>
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return <h3 key={i} style={{ marginTop: 20, marginBottom: 6, fontSize: 15, color: 'var(--navy)', borderBottom: '1px solid var(--border)', paddingBottom: 4 }}>{line.slice(3)}</h3>;
        }
        if (line.startsWith('### ')) {
          return <h4 key={i} style={{ marginTop: 14, marginBottom: 4, fontSize: 13, fontWeight: 700 }}>{line.slice(4)}</h4>;
        }
        if (line.match(/^[-*] /)) {
          return <div key={i} style={{ paddingLeft: 20, marginBottom: 3 }}>• {line.slice(2)}</div>;
        }
        if (line.match(/^\d+\. /)) {
          return <div key={i} style={{ paddingLeft: 20, marginBottom: 3 }}>{line}</div>;
        }
        if (line.trim() === '') return <div key={i} style={{ height: 8 }} />;
        return <p key={i} style={{ margin: '4px 0' }}>{line}</p>;
      })}
    </div>
  );
}

function daysSince(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

export default function MonitorPage() {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState('');

  useEffect(() => {
    getLatestDigest()
      .then((d: Digest | null) => setDigest(d))
      .catch(() => {})
      .finally(() => setLoadingDigest(false));

    getAlerts()
      .then((a: Alerts) => setAlerts(a))
      .catch(() => {})
      .finally(() => setLoadingAlerts(false));
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    setGenError('');
    try {
      const d = await generateDigest() as Digest;
      setDigest(d);
    } catch (err: unknown) {
      setGenError((err as Error).message || 'Failed to generate digest.');
    } finally {
      setGenerating(false);
    }
  }

  const totalStale = (alerts?.stale_credit.length ?? 0) + (alerts?.stale_service.length ?? 0);
  const totalAtRisk = alerts?.at_risk.length ?? 0;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1>Case Monitor</h1>
            <p>Morning digest and live alerts for stale or at-risk cases</p>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={generating}
            style={{ alignSelf: 'flex-start' }}
          >
            {generating ? '⏳ Generating…' : '⚡ Generate Digest'}
          </button>
        </div>

        {genError && <div className="alert-error" style={{ marginBottom: 16 }}>{genError}</div>}

        {/* Summary chips */}
        {alerts && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
            <div className="card" style={{ padding: '12px 18px', flex: '1 1 140px', minWidth: 140 }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>New This Week</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--navy)' }}>
                {alerts.new_this_week.credit + alerts.new_this_week.service}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>{alerts.new_this_week.credit} credit · {alerts.new_this_week.service} service</div>
            </div>
            <div className="card" style={{ padding: '12px 18px', flex: '1 1 140px', minWidth: 140, borderLeft: totalStale > 0 ? '3px solid #f59e0b' : undefined }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Stale (7+ days)</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: totalStale > 0 ? '#d97706' : 'var(--navy)' }}>{totalStale}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>no activity in a week</div>
            </div>
            <div className="card" style={{ padding: '12px 18px', flex: '1 1 140px', minWidth: 140, borderLeft: totalAtRisk > 0 ? '3px solid #ef4444' : undefined }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>At Risk (30+ days)</div>
              <div style={{ fontSize: 26, fontWeight: 700, color: totalAtRisk > 0 ? '#dc2626' : 'var(--navy)' }}>{totalAtRisk}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>open over 30 days</div>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>

          {/* Digest panel */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0 }}>Morning Digest</h3>
              {digest?.created_at && (
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                  {new Date(digest.created_at).toLocaleString()}
                </span>
              )}
            </div>
            {loadingDigest ? (
              <div className="spinner" />
            ) : digest ? (
              <MarkdownContent text={digest.content} />
            ) : (
              <div>
                <p className="empty" style={{ marginBottom: 14 }}>No digest generated yet.</p>
                <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
                  {generating ? '⏳ Generating…' : 'Generate First Digest'}
                </button>
              </div>
            )}
          </div>

          {/* Alert sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Stale credit cases */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: '#fffbeb' }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#92400e' }}>
                  Stale Credit Cases
                </span>
                {alerts && <span style={{ marginLeft: 8, fontSize: 11, color: '#b45309' }}>({alerts.stale_credit.length})</span>}
              </div>
              {loadingAlerts ? (
                <div style={{ padding: 16 }}><div className="spinner" /></div>
              ) : alerts?.stale_credit.length === 0 ? (
                <div style={{ padding: '12px 16px', fontSize: 12, color: 'var(--muted)' }}>All credit cases up to date.</div>
              ) : (
                alerts?.stale_credit.map(c => (
                  <Link key={c.id} href={`/cases/${c.id}`}
                    style={{ display: 'block', padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, color: 'inherit', textDecoration: 'none' }}
                  >
                    <div style={{ fontWeight: 600 }}>{c.case_number}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>Last activity: {daysSince(c.last_activity)}</div>
                  </Link>
                ))
              )}
            </div>

            {/* Stale service cases */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: '#fffbeb' }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#92400e' }}>
                  Stale Service Cases
                </span>
                {alerts && <span style={{ marginLeft: 8, fontSize: 11, color: '#b45309' }}>({alerts.stale_service.length})</span>}
              </div>
              {loadingAlerts ? (
                <div style={{ padding: 16 }}><div className="spinner" /></div>
              ) : alerts?.stale_service.length === 0 ? (
                <div style={{ padding: '12px 16px', fontSize: 12, color: 'var(--muted)' }}>All service cases up to date.</div>
              ) : (
                alerts?.stale_service.map(c => (
                  <Link key={c.id} href={`/services/${c.division}/${c.id}`}
                    style={{ display: 'block', padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, color: 'inherit', textDecoration: 'none' }}
                  >
                    <div style={{ fontWeight: 600 }}>{c.case_number}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>
                      {c.division} · {daysSince(c.last_activity)}
                    </div>
                  </Link>
                ))
              )}
            </div>

            {/* At-risk cases */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: '#fef2f2' }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#991b1b' }}>
                  At Risk (30+ days open)
                </span>
                {alerts && <span style={{ marginLeft: 8, fontSize: 11, color: '#b91c1c' }}>({alerts.at_risk.length})</span>}
              </div>
              {loadingAlerts ? (
                <div style={{ padding: 16 }}><div className="spinner" /></div>
              ) : alerts?.at_risk.length === 0 ? (
                <div style={{ padding: '12px 16px', fontSize: 12, color: 'var(--muted)' }}>No at-risk cases.</div>
              ) : (
                alerts?.at_risk.map(c => (
                  <Link key={c.id} href={`/cases/${c.id}`}
                    style={{ display: 'block', padding: '10px 16px', borderBottom: '1px solid var(--border)', fontSize: 12, color: 'inherit', textDecoration: 'none' }}
                  >
                    <div style={{ fontWeight: 600 }}>{c.case_number}</div>
                    <div style={{ color: '#dc2626', fontSize: 11 }}>Open {daysSince(c.last_activity)}</div>
                  </Link>
                ))
              )}
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
