'use client';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { getPortalToken } from '@/lib/portal-api';

interface Message { role: 'user' | 'assistant'; content: string; }
interface Booking { appointment_id: number; confirmed_time: string; division: string; status: string; }

async function agentChat(messages: Message[], clientId?: number): Promise<{ message: string; booking?: Booking }> {
  const token = getPortalToken() ?? (typeof window !== 'undefined' ? localStorage.getItem('aegis_token') : null);
  const res = await fetch('/api/booking/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages, client_id: clientId ?? null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

const SERVICES = [
  { label: 'Credit Repair', icon: '📊' },
  { label: 'Record Relief', icon: '⚖' },
  { label: 'Document Prep', icon: '📄' },
  { label: 'Mobile Notary', icon: '✍' },
  { label: 'Consulting', icon: '💬' },
  { label: 'Other', icon: '🔍' },
];

export default function BookPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState('');
  const [started, setStarted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  function focusInput() {
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function startChat(initialMsg: string) {
    if (loading) return;
    setStarted(true);
    setLoading(true);
    setError('');
    const userMsg: Message = { role: 'user', content: initialMsg };
    setMessages([userMsg]);
    try {
      const r = await agentChat([userMsg]);
      setMessages([userMsg, { role: 'assistant', content: r.message }]);
      if (r.booking) setBooking(r.booking);
    } catch (e: unknown) {
      setError((e as Error).message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
      focusInput();
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading || booking) return;
    const userMsg: Message = { role: 'user', content: input.trim() };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput('');
    setLoading(true);
    setError('');
    try {
      const r = await agentChat(next);
      setMessages(m => [...m, { role: 'assistant', content: r.message }]);
      if (r.booking) setBooking(r.booking);
    } catch (e: unknown) {
      setError((e as Error).message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
      focusInput();
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto' }}>
      <div style={{ marginBottom: 20 }}>
        <Link href="/portal/dashboard" style={{ color: '#64748b', fontSize: 13, textDecoration: 'none' }}>
          ← Dashboard
        </Link>
        <h2 style={{ margin: '8px 0 2px', color: '#0a2540', fontSize: 22, fontWeight: 700 }}>
          Book an Appointment
        </h2>
        <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>
          Our AI scheduling assistant will find a time that works for you — no email back-and-forth.
        </p>
      </div>

      {/* Quick-start service picker (before chat begins) */}
      {!started && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 13, color: '#475569', marginBottom: 10, fontWeight: 500 }}>
            What can we help you with?
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {SERVICES.map(s => (
              <button
                key={s.label}
                onClick={() => startChat(`I need to schedule an appointment for ${s.label}.`)}
                style={{
                  background: '#fff', border: '1px solid #e2e8f0',
                  borderRadius: 20, padding: '7px 14px', fontSize: 13,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                  color: '#1e293b', fontWeight: 500,
                  transition: 'border-color 0.15s, background 0.15s',
                }}
                onMouseOver={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = '#0a2540'; (e.currentTarget as HTMLButtonElement).style.background = '#f8fafc'; }}
                onMouseOut={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = '#e2e8f0'; (e.currentTarget as HTMLButtonElement).style.background = '#fff'; }}
              >
                <span>{s.icon}</span>{s.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat window */}
      <div style={{
        background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
        display: 'flex', flexDirection: 'column',
        height: started ? 480 : 420,
        boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
        transition: 'height 0.2s ease',
      }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 8px' }}>

          {/* Empty state before start */}
          {!started && !loading && (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', textAlign: 'center' }}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>📅</div>
              <div style={{ fontSize: 14, fontWeight: 500, color: '#64748b' }}>Pick a service above or type a message to get started</div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: 12,
            }}>
              {m.role === 'assistant' && (
                <div style={{
                  width: 28, height: 28, borderRadius: '50%', background: '#0a2540',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, marginRight: 8, flexShrink: 0, marginTop: 2,
                }}>⚖</div>
              )}
              <div style={{
                maxWidth: '78%',
                background: m.role === 'user' ? '#0a2540' : '#f1f5f9',
                color: m.role === 'user' ? '#fff' : '#1e293b',
                borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '4px 16px 16px 16px',
                padding: '10px 14px', fontSize: 14, lineHeight: 1.55,
                whiteSpace: 'pre-wrap',
              }}>
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#0a2540', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>⚖</div>
              <div style={{ background: '#f1f5f9', borderRadius: '4px 16px 16px 16px', padding: '12px 16px' }}>
                <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  {[0, 1, 2].map(i => (
                    <span key={i} style={{
                      width: 7, height: 7, borderRadius: '50%', background: '#94a3b8', display: 'inline-block',
                      animation: 'dotpulse 1.2s ease-in-out infinite',
                      animationDelay: `${i * 0.2}s`,
                    }} />
                  ))}
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Booking confirmation */}
        {booking && (
          <div style={{
            margin: '0 12px 10px',
            background: '#f0fdf4', border: '1px solid #86efac',
            borderRadius: 8, padding: '12px 16px', fontSize: 13,
          }}>
            <div style={{ fontWeight: 700, color: '#14532d', marginBottom: 2 }}>
              ✓ Appointment Confirmed — #{booking.appointment_id}
            </div>
            <div style={{ color: '#166534' }}>
              {booking.division} &middot; {booking.confirmed_time}
            </div>
            <div style={{ marginTop: 6, fontSize: 12, color: '#15803d' }}>
              Our team will reach out to confirm the call details. See you then!
            </div>
          </div>
        )}

        {error && (
          <div style={{ margin: '0 12px 8px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#991b1b' }}>
            {error}
          </div>
        )}

        {/* Input */}
        <form onSubmit={send} style={{ display: 'flex', gap: 8, padding: '8px 12px 12px', borderTop: '1px solid #f1f5f9' }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={booking ? 'Appointment booked!' : started ? 'Reply…' : 'Or type a message to start…'}
            disabled={loading || !!booking}
            onFocus={() => { if (!started && input.trim()) return; }}
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 24,
              border: '1px solid #e2e8f0', fontSize: 14, outline: 'none',
              background: booking ? '#f8fafc' : '#fff',
              color: '#1e293b',
            }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                if (!started && input.trim()) {
                  e.preventDefault();
                  startChat(input.trim());
                  setInput('');
                }
              }
            }}
          />
          <button
            type={started ? 'submit' : 'button'}
            onClick={!started && input.trim() ? () => { startChat(input.trim()); setInput(''); } : undefined}
            disabled={loading || !input.trim() || !!booking}
            style={{
              background: '#0a2540', color: '#fff', border: 'none',
              borderRadius: 24, padding: '10px 20px', fontSize: 14,
              fontWeight: 600,
              cursor: loading || !input.trim() || !!booking ? 'default' : 'pointer',
              opacity: loading || !input.trim() || !!booking ? 0.45 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            Send
          </button>
        </form>
      </div>

      <p style={{ marginTop: 12, fontSize: 11, color: '#94a3b8', textAlign: 'center' }}>
        Monday – Friday · 9 AM – 5 PM Eastern · All appointments by phone or video call
      </p>

      <style>{`
        @keyframes dotpulse {
          0%, 100% { opacity: 0.25; transform: scale(0.9); }
          50%       { opacity: 1;    transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
}
