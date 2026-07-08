'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface DifyConfig {
  receptionist_token: string;
  base_url: string;
  configured: boolean;
}

export default function ReceptionistPage() {
  const [config, setConfig] = useState<DifyConfig | null>(null);
  const [showEmbed, setShowEmbed] = useState(false);

  useEffect(() => {
    fetch('/api/dify/config').then(r => r.json()).then(setConfig).catch(() => {});
  }, []);

  const embedUrl = config?.receptionist_token
    ? `${config.base_url?.replace('/v1', '') || 'https://udify.app'}/chatbot/${config.receptionist_token}`
    : null;

  return (
    <div style={{
      minHeight: '100vh', background: '#0a1628',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      color: '#fff',
    }}>
      {/* Header */}
      <header style={{
        padding: '18px 32px', display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 26 }}>⚖</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, letterSpacing: 0.3 }}>
              Cruel &amp; Associates
            </div>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 0.5 }}>
              CREDIT SERVICES ORGANIZATION
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', fontSize: 13 }}>
          <a href="/portal/login" style={{ color: '#93c5fd', textDecoration: 'none' }}>Client Portal</a>
          <a href="/portal/book" style={{
            background: '#2563eb', color: '#fff', padding: '8px 18px',
            borderRadius: 6, textDecoration: 'none', fontWeight: 600, fontSize: 13,
          }}>Book Appointment</a>
        </div>
      </header>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '60px 24px 40px' }}>
        {/* Hero */}
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{
            display: 'inline-block', background: 'rgba(37,99,235,0.15)',
            border: '1px solid rgba(37,99,235,0.3)', borderRadius: 20,
            padding: '4px 14px', fontSize: 12, color: '#93c5fd',
            letterSpacing: 0.8, marginBottom: 20, fontWeight: 600,
          }}>
            AVAILABLE 24 / 7
          </div>
          <h1 style={{ fontSize: 40, fontWeight: 800, lineHeight: 1.15, margin: '0 0 16px', letterSpacing: -0.5 }}>
            Your AI Credit Advisor
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 17, maxWidth: 540, margin: '0 auto', lineHeight: 1.6 }}>
            Ask about credit repair, our services, pricing, or schedule an appointment
            — any time, no hold music.
          </p>
        </div>

        {/* Chat section */}
        {embedUrl ? (
          <div style={{
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 16, overflow: 'hidden', marginBottom: 48,
          }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 6px #22c55e' }} />
              <span style={{ fontSize: 13, color: '#94a3b8' }}>AI Receptionist — Online</span>
            </div>
            <iframe
              src={embedUrl}
              width="100%"
              height="520"
              style={{ border: 'none', display: 'block' }}
              allow="microphone"
              title="Aegis AI Receptionist"
            />
          </div>
        ) : (
          /* Fallback when Dify isn't configured */
          <div style={{
            background: 'rgba(37,99,235,0.08)', border: '1px solid rgba(37,99,235,0.25)',
            borderRadius: 16, padding: '40px 32px', textAlign: 'center', marginBottom: 48,
          }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>📅</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>
              Ready to get started?
            </h2>
            <p style={{ color: '#94a3b8', fontSize: 15, marginBottom: 28, maxWidth: 400, margin: '0 auto 28px' }}>
              Our team is available Monday–Friday, 9 AM – 5 PM Eastern.
              Book online or call us directly.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              <a href="/portal/book" style={{
                background: '#2563eb', color: '#fff', padding: '12px 28px',
                borderRadius: 8, textDecoration: 'none', fontWeight: 700, fontSize: 15,
              }}>
                Book an Appointment
              </a>
              <a href="/portal/register" style={{
                background: 'transparent', color: '#93c5fd', padding: '12px 28px',
                borderRadius: 8, textDecoration: 'none', fontWeight: 600, fontSize: 15,
                border: '1px solid rgba(147,197,253,0.4)',
              }}>
                Create Client Account
              </a>
            </div>
          </div>
        )}

        {/* Services grid */}
        <div style={{ marginBottom: 48 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, color: '#e2e8f0' }}>
            Our Services
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
            {[
              { icon: '📊', title: 'Credit Repair', desc: 'Remove inaccuracies, build your score' },
              { icon: '⚖', title: 'Record Relief', desc: 'Criminal record & background check issues' },
              { icon: '📄', title: 'Document Prep', desc: 'Legal and financial document preparation' },
              { icon: '✍', title: 'Mobile Notary', desc: 'Notary services at your location' },
              { icon: '🏛', title: 'Judgment Relief', desc: 'Judgment removal and debt resolution' },
              { icon: '💼', title: 'Consulting', desc: 'Financial strategy and planning' },
            ].map(s => (
              <div key={s.title} style={{
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 10, padding: '16px 18px',
              }}>
                <div style={{ fontSize: 22, marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{s.title}</div>
                <div style={{ color: '#64748b', fontSize: 13 }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA + disclaimer */}
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 28,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexWrap: 'wrap', gap: 16,
        }}>
          <div style={{ fontSize: 12, color: '#475569', maxWidth: 560, lineHeight: 1.6 }}>
            <strong style={{ color: '#64748b' }}>Non-Attorney Notice:</strong>{' '}
            Cruel &amp; Associates is a credit services organization, not a law firm. We do not provide
            legal advice. Services governed by the Credit Repair Organizations Act (15 U.S.C. §§1679–1679j).
          </div>
          <a href="/portal/login" style={{ color: '#64748b', fontSize: 13, textDecoration: 'none' }}>
            Existing client? Sign in →
          </a>
        </div>
      </div>
    </div>
  );
}
