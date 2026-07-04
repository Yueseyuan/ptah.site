'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { runCaseResearch, listCaseResearch } from '@/lib/api';

interface ResearchDoc {
  id: number;
  title: string;
  content: string;
  created_at: string | null;
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

export default function CaseResearchPage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);

  const [query, setQuery] = useState('');
  const [context, setContext] = useState('');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [docs, setDocs] = useState<ResearchDoc[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    listCaseResearch(caseId)
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, [caseId]);

  async function handleResearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setRunning(true);
    setError('');
    try {
      const result = await runCaseResearch(caseId, query.trim(), context.trim() || undefined);
      const newDoc: ResearchDoc = {
        id: result.document_id,
        title: result.title,
        content: result.content,
        created_at: new Date().toISOString(),
      };
      setDocs(prev => [newDoc, ...prev]);
      setOpenId(newDoc.id);
      setQuery('');
      setContext('');
    } catch (err: unknown) {
      const e = err as Error & { response?: { status: number } };
      if (e.response?.status === 503) {
        setError('AI service not configured. Ensure ANTHROPIC_API_KEY is set in Railway.');
      } else {
        setError(e.message || 'Research failed. Please try again.');
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <CaseNav caseId={caseId} />

        <div className="page-header">
          <div>
            <h1>Research Agent</h1>
            <p>Multi-step web research — searches public records, legal precedents, and creditor data using AI</p>
          </div>
        </div>

        {/* Query form */}
        <div className="card" style={{ marginBottom: 24 }}>
          <form onSubmit={handleResearch}>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
                Research Query *
              </label>
              <textarea
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="e.g. Find court judgments for Capital One in Broward County FL in the last 3 years"
                rows={3}
                disabled={running}
                style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical' }}
                className="form-control"
              />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
                Additional Context <span style={{ fontWeight: 400, color: 'var(--muted)' }}>(optional)</span>
              </label>
              <textarea
                value={context}
                onChange={e => setContext(e.target.value)}
                placeholder="e.g. Client is disputing a $4,200 collection account. Creditor: Midland Funding LLC. State: Florida."
                rows={2}
                disabled={running}
                style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical' }}
                className="form-control"
              />
            </div>
            {error && <div className="alert-error" style={{ marginBottom: 12 }}>{error}</div>}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button type="submit" className="btn btn-primary" disabled={running || !query.trim()}>
                {running ? '🔍 Researching…' : '🔍 Run Research'}
              </button>
              {running && (
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                  Searching web sources — this takes 15–30 seconds…
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Research history */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {loadingHistory ? (
            <div className="spinner" />
          ) : docs.length === 0 ? (
            <div className="card">
              <p className="empty">No research reports yet. Run your first query above.</p>
            </div>
          ) : (
            docs.map(doc => (
              <div key={doc.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <button
                  onClick={() => setOpenId(openId === doc.id ? null : doc.id)}
                  style={{
                    width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                    padding: '14px 18px', display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', textAlign: 'left',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--navy)' }}>{doc.title}</div>
                    {doc.created_at && (
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                        {new Date(doc.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: 18, color: 'var(--muted)', flexShrink: 0 }}>
                    {openId === doc.id ? '▲' : '▼'}
                  </span>
                </button>
                {openId === doc.id && (
                  <div style={{ padding: '0 18px 18px', borderTop: '1px solid var(--border)' }}>
                    <MarkdownContent text={doc.content} />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
