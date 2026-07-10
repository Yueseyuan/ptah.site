'use client';

export default function CriminalPortalEntryPage() {
  return (
    <div style={{
      minHeight: '100vh', background: '#1a1a2e',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 540, textAlign: 'center' }}>
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontSize: 42, marginBottom: 14 }}>⚖️</div>
          <h1 style={{ color: '#fff', fontSize: 24, fontWeight: 800, margin: '0 0 8px', letterSpacing: -0.5 }}>
            Criminal Record Relief
          </h1>
          <p style={{ color: '#a78bfa', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
            Expungements, pardons, and record sealing — handled with care.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 32 }}>
          <a href="/criminal-portal/login" style={{
            background: '#7c3aed', color: '#fff', textDecoration: 'none',
            padding: '16px 24px', borderRadius: 12, fontSize: 15, fontWeight: 700,
            display: 'block', transition: 'background 0.15s',
          }}>
            Sign In to My Portal →
          </a>
          <a href="/criminal-portal/register" style={{
            background: 'rgba(255,255,255,0.08)', color: '#c4b5fd',
            border: '1px solid rgba(255,255,255,0.2)', textDecoration: 'none',
            padding: '14px 24px', borderRadius: 12, fontSize: 14, fontWeight: 600,
            display: 'block',
          }}>
            Create New Account
          </a>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 12, padding: '20px 24px', marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            {[
              { icon: '📝', label: 'Intake', desc: 'Submit your case details online' },
              { icon: '🔍', label: 'Review', desc: 'We assess eligibility & options' },
              { icon: '✅', label: 'Resolution', desc: 'Track progress to completion' },
            ].map(step => (
              <div key={step.label}>
                <div style={{ fontSize: 22, marginBottom: 6 }}>{step.icon}</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0', marginBottom: 3 }}>{step.label}</div>
                <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>{step.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: 12, color: '#475569' }}>
          Already submitted an intake through the main portal?{' '}
          <a href="/portal/login" style={{ color: '#a78bfa', textDecoration: 'none' }}>Sign in there instead</a>
        </div>

        <div style={{ marginTop: 20 }}>
          <a href="/" style={{ color: '#334155', fontSize: 12, textDecoration: 'none' }}>← Back to main site</a>
        </div>
      </div>
    </div>
  );
}
