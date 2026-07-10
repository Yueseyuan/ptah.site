'use client';

export default function JudgmentPortalEntryPage() {
  return (
    <div style={{
      minHeight: '100vh', background: '#1c1917',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 560, textAlign: 'center' }}>
        <div style={{ marginBottom: 36 }}>
          <div style={{ fontSize: 40, marginBottom: 14 }}>⚖️</div>
          <h1 style={{ color: '#fff', fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: -0.5 }}>
            Judgment &amp; Asset Recovery
          </h1>
          <p style={{ color: '#C9A84C', fontSize: 14, margin: '0 0 6px', lineHeight: 1.6 }}>
            You won in court. Now let&apos;s collect.
          </p>
          <p style={{ color: '#78716c', fontSize: 13, margin: 0, lineHeight: 1.6 }}>
            Wage garnishment, bank levies, asset tracing, estate recovery — we enforce what you&apos;re owed.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 36 }}>
          <a href="/judgment-portal/login" style={{
            background: '#C9A84C', color: '#1c1917', textDecoration: 'none',
            padding: '15px 24px', borderRadius: 10, fontSize: 15, fontWeight: 800,
            display: 'block',
          }}>
            Sign In to My Portal →
          </a>
          <a href="/judgment-portal/register" style={{
            background: 'rgba(255,255,255,0.07)', color: '#d6d3d1',
            border: '1px solid rgba(255,255,255,0.15)', textDecoration: 'none',
            padding: '13px 24px', borderRadius: 10, fontSize: 14, fontWeight: 600,
            display: 'block',
          }}>
            Create New Account
          </a>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 28 }}>
          {[
            { icon: '🔍', title: 'Asset Tracing', desc: 'We locate bank accounts, property, vehicles, and hidden assets' },
            { icon: '📋', title: 'Enforcement', desc: 'Wage garnishment, bank levies, and property liens filed properly' },
            { icon: '💰', title: 'Recovery', desc: 'We collect and get the money to you' },
          ].map(s => (
            <div key={s.title} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '16px 14px' }}>
              <div style={{ fontSize: 22, marginBottom: 8 }}>{s.icon}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#C9A84C', marginBottom: 4 }}>{s.title}</div>
              <div style={{ fontSize: 11, color: '#78716c', lineHeight: 1.5 }}>{s.desc}</div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: 12, color: '#44403c' }}>
          <a href="/" style={{ color: '#57534e', textDecoration: 'none' }}>← Back to main site</a>
        </div>
      </div>
    </div>
  );
}
