'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listStrategy, generateStrategy, updateStrategyItem } from '@/lib/api';

interface StrategyItem { id: number; priority: number; strategy_type: string; title: string; description: string; action_items: string[]; estimated_timeline: string; status: string; ai_generated: boolean; }

export default function StrategyPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [items, setItems] = useState<StrategyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  function load() { listStrategy(caseId).then(setItems).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function generate() {
    setGenerating(true); setError(''); setSuccess('');
    try {
      const r = await generateStrategy(caseId);
      setSuccess(`Generated ${r.items_generated} strategy items.`);
      load();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const d = e.response?.data?.detail;
      setError(typeof d === 'string' ? d : e.message || 'Strategy generation failed. Ensure findings exist and ANTHROPIC_API_KEY is configured.');
    } finally { setGenerating(false); }
  }

  async function setStatus(itemId: number, status: string) {
    await updateStrategyItem(itemId, { status });
    load();
  }

  const prioColor: Record<number, string> = { 1: '#fee2e2', 2: '#fef3c7', 3: '#dbeafe' };
  const prioLabel: Record<number, string> = { 1: 'HIGH', 2: 'MEDIUM', 3: 'LOW' };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Strategy</h1><p>AI-generated credit restoration action plan</p></div>
          <button className="btn btn-primary" onClick={generate} disabled={generating}>{generating ? 'Generating…' : '⚡ Generate Strategy'}</button>
        </div>
        <CaseNav caseId={caseId} />

        <div className="disclosure-banner">All strategies are administrative recommendations requiring investigator and client review. Not legal advice.</div>

        {error && <div className="alert-error">{error}</div>}
        {success && <div className="alert-success">{success}</div>}

        {loading ? <div className="spinner" /> : items.length === 0 ? (
          <div className="card"><p className="empty">No strategy items yet. Generate findings first, then generate strategy.</p></div>
        ) : (
          items.map(item => (
            <div key={item.id} className="card" style={{ marginBottom: 12, borderLeft: `4px solid ${item.priority === 1 ? 'var(--danger)' : item.priority === 2 ? 'var(--warning)' : 'var(--info)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ background: prioColor[item.priority], padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>P{item.priority} {prioLabel[item.priority]}</span>
                  <span className="badge badge-pending">{item.strategy_type}</span>
                  {item.ai_generated && <span style={{ fontSize: 10, color: 'var(--muted)' }}>AI</span>}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {item.estimated_timeline && <span style={{ fontSize: 12, color: 'var(--muted)' }}>~{item.estimated_timeline}</span>}
                  <select value={item.status} onChange={e => setStatus(item.id, e.target.value)}
                    style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, border: '1px solid var(--border)' }}>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </div>
              </div>
              <h4 style={{ color: 'var(--navy)', marginBottom: 6 }}>{item.title}</h4>
              {item.description && <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 10 }}>{item.description}</p>}
              {item.action_items?.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {item.action_items.map((a, i) => <li key={i} style={{ fontSize: 13, marginBottom: 4 }}>{a}</li>)}
                </ul>
              )}
            </div>
          ))
        )}
      </main>
    </div>
  );
}
