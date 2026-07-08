'use client';
import { useState, useRef } from 'react';
import Sidebar from '@/components/Sidebar';

type Tab = 'librechat' | 'openhands' | 'voice';

interface TaskResult {
  conversation_id?: string;
  status?: string;
  result?: unknown;
  error?: string;
}

export default function StaffAIPage() {
  const [tab, setTab] = useState<Tab>('librechat');
  const [librechatUrl, setLibrechatUrl] = useState('');
  const [task, setTask] = useState('');
  const [taskMode, setTaskMode] = useState('document');
  const [context, setContext] = useState('');
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [taskError, setTaskError] = useState('');
  const [voiceInput, setVoiceInput] = useState('');
  const [voiceResult, setVoiceResult] = useState('');
  const [voiceLoading, setVoiceLoading] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const token = typeof window !== 'undefined' ? localStorage.getItem('aegis_token') : null;

  async function apiFetch(path: string, body: unknown) {
    const res = await fetch(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({})) as { detail?: string };
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function runOpenHandsTask(e: React.FormEvent) {
    e.preventDefault();
    if (!task.trim()) return;
    setTaskLoading(true); setTaskError(''); setTaskResult(null);
    try {
      const r = await apiFetch('/api/openhands/task', { task, context, mode: taskMode });
      setTaskResult(r);
    } catch (e: unknown) {
      setTaskError((e as Error).message);
    } finally { setTaskLoading(false); }
  }

  async function pollTask(id: string) {
    if (!id) return;
    try {
      const res = await fetch(`/api/openhands/task/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const r = await res.json();
      setTaskResult(r);
    } catch {/* silent */}
  }

  async function runVoiceChat(e: React.FormEvent) {
    e.preventDefault();
    if (!voiceInput.trim()) return;
    setVoiceLoading(true);
    try {
      const r = await apiFetch('/api/voice/chat', {
        messages: [{ role: 'user', content: voiceInput }],
      });
      setVoiceResult(r.message || JSON.stringify(r));
    } catch (e: unknown) {
      setVoiceResult(`Error: ${(e as Error).message}`);
    } finally { setVoiceLoading(false); }
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>AI Workspace</h1>
          <p>LibreChat · OpenHands · Voice Assistant</p>
        </div>

        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
          {([
            { key: 'librechat', label: '💬 LibreChat', desc: 'Multi-model AI chat' },
            { key: 'openhands', label: '🤖 OpenHands', desc: 'Autonomous document agent' },
            { key: 'voice',     label: '🎙 Voice AI',  desc: 'OpenJarvis voice assistant' },
          ] as { key: Tab; label: string; desc: string }[]).map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                padding: '8px 16px', border: 'none', background: 'transparent',
                borderBottom: tab === t.key ? '2px solid var(--primary)' : '2px solid transparent',
                color: tab === t.key ? 'var(--primary)' : 'var(--muted)',
                fontWeight: tab === t.key ? 700 : 400,
                cursor: 'pointer', fontSize: 13, marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* LibreChat tab */}
        {tab === 'librechat' && (
          <div>
            {librechatUrl ? (
              <div className="card" style={{ padding: 0, overflow: 'hidden', height: 680 }}>
                <iframe
                  ref={iframeRef}
                  src={librechatUrl}
                  width="100%" height="100%"
                  style={{ border: 'none', display: 'block' }}
                  title="LibreChat"
                />
              </div>
            ) : (
              <div className="card">
                <h3>Connect LibreChat</h3>
                <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 16 }}>
                  LibreChat is a self-hosted multi-model AI chat interface. Deploy it on Railway
                  using the one-click template, then paste your instance URL below.
                </p>
                <div style={{ marginBottom: 16 }}>
                  <a
                    href="https://railway.com/deploy/librechat"
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-primary btn-sm"
                  >
                    Deploy LibreChat on Railway →
                  </a>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="url"
                    placeholder="https://librechat-production.up.railway.app"
                    style={{ flex: 1, padding: '8px 12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}
                    id="lc-url"
                  />
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      const el = document.getElementById('lc-url') as HTMLInputElement;
                      if (el?.value) setLibrechatUrl(el.value);
                    }}
                  >
                    Connect
                  </button>
                </div>
                <div className="card" style={{ marginTop: 20, background: 'var(--bg)' }}>
                  <h4 style={{ marginBottom: 8 }}>Once deployed, set in Railway Variables:</h4>
                  <code style={{ fontSize: 12, display: 'block', whiteSpace: 'pre', color: 'var(--muted)' }}>
{`LIBRECHAT_URL=https://your-librechat.railway.app
LIBRECHAT_API_KEY=your-librechat-api-key`}
                  </code>
                </div>
              </div>
            )}
          </div>
        )}

        {/* OpenHands tab */}
        {tab === 'openhands' && (
          <div className="card">
            <h3>OpenHands Autonomous Agent</h3>
            <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 18 }}>
              Dispatch a task to the OpenHands AI — it writes, edits, and analyzes autonomously.
              Use for dispute letter drafting, document analysis, or research tasks.
            </p>
            {!localStorage.getItem('aegis_token') ? null : (
              <form onSubmit={runOpenHandsTask}>
                <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                  {['document', 'analysis', 'research'].map(m => (
                    <label key={m} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                      <input type="radio" name="mode" value={m} checked={taskMode === m} onChange={() => setTaskMode(m)} />
                      {m.charAt(0).toUpperCase() + m.slice(1)}
                    </label>
                  ))}
                </div>
                <div className="form-group">
                  <label>Task Description *</label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Draft a dispute letter for a collection account from PORTFOLIO RECOVERY dated 2024-01-15 on Equifax for client John Smith"
                    value={task}
                    onChange={e => setTask(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Additional Context (optional)</label>
                  <textarea
                    rows={2}
                    placeholder="Paste relevant case notes, tradeline details, or client info here…"
                    value={context}
                    onChange={e => setContext(e.target.value)}
                  />
                </div>
                {taskError && <div className="alert-error" style={{ marginBottom: 12 }}>{taskError}</div>}
                <button type="submit" className="btn btn-primary" disabled={taskLoading}>
                  {taskLoading ? 'Dispatching…' : '⚡ Run Task'}
                </button>
              </form>
            )}

            {taskResult && (
              <div style={{ marginTop: 20, padding: 16, background: 'var(--bg)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <strong style={{ fontSize: 13 }}>
                    Task {taskResult.conversation_id} — {taskResult.status}
                  </strong>
                  {taskResult.status === 'running' && taskResult.conversation_id && (
                    <button className="btn btn-outline btn-sm" onClick={() => pollTask(taskResult.conversation_id!)}>
                      Refresh
                    </button>
                  )}
                </div>
                {taskResult.result && (
                  <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', color: 'var(--muted)', maxHeight: 300, overflow: 'auto' }}>
                    {typeof taskResult.result === 'string' ? taskResult.result : JSON.stringify(taskResult.result, null, 2)}
                  </pre>
                )}
                {!taskResult.result && taskResult.status === 'running' && (
                  <p style={{ fontSize: 13, color: 'var(--muted)' }}>
                    Task is running. Check back in 30–60 seconds.
                  </p>
                )}
              </div>
            )}

            <div className="card" style={{ marginTop: 20, background: 'var(--bg)' }}>
              <strong style={{ fontSize: 12 }}>Setup required:</strong>
              <code style={{ fontSize: 12, display: 'block', marginTop: 6, color: 'var(--muted)' }}>
                OPENHANDS_API_KEY=your-key  # from app.all-hands.dev
              </code>
            </div>
          </div>
        )}

        {/* Voice AI tab */}
        {tab === 'voice' && (
          <div className="card">
            <h3>Voice AI — OpenJarvis</h3>
            <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 18 }}>
              OpenJarvis is a local voice-first AI assistant. Run it as a sidecar on your
              workstation or server, then it&apos;s available as an OpenAI-compatible endpoint.
            </p>
            <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: '14px 16px', marginBottom: 18, fontSize: 13 }}>
              <strong>Quick start:</strong>
              <pre style={{ margin: '8px 0 0', color: 'var(--muted)', fontSize: 12 }}>
{`pip install OpenJarvis
jarvis serve --port 8765`}
              </pre>
            </div>
            <form onSubmit={runVoiceChat}>
              <div className="form-group">
                <label>Send a message to OpenJarvis</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    value={voiceInput}
                    onChange={e => setVoiceInput(e.target.value)}
                    placeholder="Ask anything…"
                    style={{ flex: 1, padding: '8px 12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}
                  />
                  <button type="submit" className="btn btn-primary" disabled={voiceLoading || !voiceInput.trim()}>
                    {voiceLoading ? '…' : 'Send'}
                  </button>
                </div>
              </div>
            </form>
            {voiceResult && (
              <div style={{ marginTop: 14, padding: 14, background: 'var(--bg)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {voiceResult}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
