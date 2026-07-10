'use client';
import { useRouter } from 'next/navigation';

export default function NotaryPortalEntryPage() {
  const router = useRouter();

  return (
    <div style={{
      minHeight: '100vh', background: '#0f2d52',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 580, textAlign: 'center' }}>
        <div style={{ marginBottom: 40 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🖊️</div>
          <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: -0.5 }}>
            Cruel &amp; Associates
          </h1>
          <div style={{ color: '#93c5fd', fontSize: 13, letterSpacing: 1.5, textTransform: 'uppercase', fontWeight: 600 }}>
            Notary Portal
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <button
            onClick={() => router.push('/notary-portal/login')}
            style={{
              background: '#fff', border: 'none', borderRadius: 14,
              padding: '32px 20px', cursor: 'pointer', textAlign: 'center',
              transition: 'transform 0.1s',
            }}
            onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-2px)')}
            onMouseLeave={e => (e.currentTarget.style.transform = 'translateY(0)')}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>📋</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#0f2d52', marginBottom: 6 }}>I'm a Notary</div>
            <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.5 }}>
              Access your signing orders, manage your schedule, and update your profile.
            </div>
          </button>

          <button
            onClick={() => router.push('/notary-portal/client')}
            style={{
              background: 'rgba(255,255,255,0.12)', border: '2px solid rgba(255,255,255,0.25)',
              borderRadius: 14, padding: '32px 20px', cursor: 'pointer', textAlign: 'center',
              transition: 'transform 0.1s',
            }}
            onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-2px)')}
            onMouseLeave={e => (e.currentTarget.style.transform = 'translateY(0)')}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>🏠</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', marginBottom: 6 }}>I Need a Signing</div>
            <div style={{ fontSize: 12, color: '#93c5fd', lineHeight: 1.5 }}>
              Track your closing appointment, view documents, and confirm your signing details.
            </div>
          </button>
        </div>

        <div style={{ marginTop: 32, color: '#64748b', fontSize: 12 }}>
          Notary professional?{' '}
          <a href="/notary-portal/register" style={{ color: '#93c5fd', textDecoration: 'none', fontWeight: 600 }}>
            Create an account →
          </a>
        </div>

        <div style={{ marginTop: 24 }}>
          <a href="/" style={{ color: '#475569', fontSize: 12, textDecoration: 'none' }}>← Back to main site</a>
        </div>
      </div>
    </div>
  );
}
