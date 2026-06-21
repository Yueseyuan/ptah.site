export default function HomePage() {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#07090f',
      color: '#e8eaf0',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      {/* Nav */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        padding: '0 48px', height: 68,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(7,9,15,0.92)', backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(201,168,76,0.12)',
      }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#c9a84c', letterSpacing: 1 }}>
            CRUEL & ASSOCIATES
          </div>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 3, textTransform: 'uppercase', marginTop: 2 }}>
            Consumer Rights Consulting
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <a href="/portal/login" style={{
            padding: '8px 20px', border: '1px solid rgba(201,168,76,0.4)',
            color: '#c9a84c', borderRadius: 4, fontSize: 13, fontWeight: 600,
            textDecoration: 'none', transition: 'all 0.15s',
          }}>
            Client Login
          </a>
          <a href="/portal/register" style={{
            padding: '8px 20px', background: '#c9a84c',
            color: '#07090f', borderRadius: 4, fontSize: 13, fontWeight: 700,
            textDecoration: 'none',
          }}>
            Get Started
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '120px 48px 80px',
      }}>
        <div style={{
          display: 'inline-block', fontSize: 10, fontWeight: 700,
          letterSpacing: 3, textTransform: 'uppercase', color: '#c9a84c',
          background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.2)',
          padding: '5px 14px', borderRadius: 20, marginBottom: 32, width: 'fit-content',
        }}>
          FCRA · FDCPA · Consumer Advocacy
        </div>

        <h1 style={{
          fontSize: 'clamp(36px, 6vw, 80px)', fontWeight: 900,
          lineHeight: 1.05, letterSpacing: -2, maxWidth: 800, margin: '0 0 24px',
        }}>
          Know Your Rights.<br />
          <span style={{
            background: 'linear-gradient(135deg, #c9a84c, #e6c96e)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            Fight Back.
          </span>
        </h1>

        <p style={{
          fontSize: 18, color: '#8a90a0', lineHeight: 1.8,
          maxWidth: 540, fontWeight: 300, marginBottom: 40,
        }}>
          We prepare legally grounded dispute correspondence under the FCRA and FDCPA,
          holding credit bureaus and debt collectors accountable — on your behalf.
        </p>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <a href="/portal/register" style={{
            padding: '15px 36px', background: '#c9a84c', color: '#07090f',
            fontWeight: 800, fontSize: 15, borderRadius: 4, textDecoration: 'none',
            letterSpacing: 0.3,
          }}>
            Start Your Case →
          </a>
          <a href="/portal/login" style={{
            padding: '15px 36px', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.15)', color: '#e8eaf0',
            fontSize: 15, borderRadius: 4, textDecoration: 'none',
          }}>
            Client Portal
          </a>
        </div>

        {/* Stats */}
        <div style={{
          display: 'flex', gap: 48, marginTop: 72,
          paddingTop: 40, borderTop: '1px solid rgba(201,168,76,0.12)',
          flexWrap: 'wrap',
        }}>
          {[
            { num: '30', suffix: ' days', label: 'Bureau Response Window (FCRA)' },
            { num: '$1,000', suffix: '', label: 'Statutory Damages per FDCPA Violation' },
            { num: '3', suffix: ' bureaus', label: 'Experian · Equifax · TransUnion' },
            { num: '$149', suffix: '/mo', label: 'Flat Monthly Retainer' },
          ].map(s => (
            <div key={s.label}>
              <div style={{
                fontSize: 28, fontWeight: 900,
                background: 'linear-gradient(135deg, #c9a84c, #e6c96e)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>
                {s.num}<span style={{ fontSize: 16 }}>{s.suffix}</span>
              </div>
              <div style={{ fontSize: 11, color: '#4a5060', marginTop: 4, letterSpacing: 0.3 }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Divisions */}
      <section style={{ padding: '80px 48px', background: '#07090f' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 16 }}>
          Our Services
        </div>
        <h2 style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 800, marginBottom: 16, maxWidth: 600 }}>
          Three Ways We Put Money Back in Your Pocket
        </h2>
        <p style={{ color: '#64748b', fontSize: 16, marginBottom: 48, maxWidth: 540 }}>
          Whether it's bad credit, an unpaid judgment, or surplus funds from a foreclosure — we know how to recover what's yours.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24 }}>
          {/* Credit Repair */}
          <div style={{
            background: '#0c1018', border: '1px solid rgba(201,168,76,0.25)',
            borderRadius: 10, padding: '36px 32px',
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ fontSize: 36, marginBottom: 18 }}>📑</div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 10 }}>
              Division I
            </div>
            <h3 style={{ fontSize: 22, fontWeight: 800, color: '#e8eaf0', marginBottom: 14, lineHeight: 1.2 }}>
              Credit Repair &amp; Consumer Rights
            </h3>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.75, marginBottom: 28, flex: 1 }}>
              FCRA &amp; FDCPA dispute correspondence — bureau letters, debt collector cease &amp; desist, CFPB complaints, and affidavits of truth. Flat monthly retainer, no hourly billing.
            </p>
            <a href="/portal/register" style={{
              display: 'inline-block', padding: '12px 24px',
              background: '#c9a84c', color: '#07090f',
              fontWeight: 800, fontSize: 14, borderRadius: 5,
              textDecoration: 'none', textAlign: 'center',
            }}>
              Start Your Case →
            </a>
          </div>

          {/* Judgment Recovery */}
          <div style={{
            background: '#0c1018', border: '1px solid rgba(201,168,76,0.15)',
            borderRadius: 10, padding: '36px 32px',
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ fontSize: 36, marginBottom: 18 }}>⚖️</div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 10 }}>
              Division II
            </div>
            <h3 style={{ fontSize: 22, fontWeight: 800, color: '#e8eaf0', marginBottom: 14, lineHeight: 1.2 }}>
              Judgment Recovery
            </h3>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.75, marginBottom: 28, flex: 1 }}>
              Won a lawsuit but never got paid? We locate assets, file enforcement actions, and collect on dormant civil judgments — at no upfront cost. We only get paid when you do.
            </p>
            <a href="mailto:yueseyuan.cruel@cruelandassociates.site?subject=Judgment Recovery Inquiry" style={{
              display: 'inline-block', padding: '12px 24px',
              background: 'transparent', color: '#c9a84c',
              border: '1px solid rgba(201,168,76,0.4)',
              fontWeight: 700, fontSize: 14, borderRadius: 5,
              textDecoration: 'none', textAlign: 'center',
            }}>
              Contact Us →
            </a>
          </div>

          {/* Overages */}
          <div style={{
            background: '#0c1018', border: '1px solid rgba(201,168,76,0.15)',
            borderRadius: 10, padding: '36px 32px',
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ fontSize: 36, marginBottom: 18 }}>🏠</div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 10 }}>
              Division III
            </div>
            <h3 style={{ fontSize: 22, fontWeight: 800, color: '#e8eaf0', marginBottom: 14, lineHeight: 1.2 }}>
              Foreclosure Overages &amp; Surplus Funds
            </h3>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.75, marginBottom: 28, flex: 1 }}>
              When a foreclosed property sells for more than the debt owed, the surplus belongs to the former owner — not the bank. We track down and recover those overage funds on your behalf.
            </p>
            <a href="mailto:yueseyuan.cruel@cruelandassociates.site?subject=Surplus Funds Inquiry" style={{
              display: 'inline-block', padding: '12px 24px',
              background: 'transparent', color: '#c9a84c',
              border: '1px solid rgba(201,168,76,0.4)',
              fontWeight: 700, fontSize: 14, borderRadius: 5,
              textDecoration: 'none', textAlign: 'center',
            }}>
              Contact Us →
            </a>
          </div>
        </div>
      </section>

      {/* Credit Repair Details */}
      <section style={{ padding: '80px 48px', background: '#0c1018' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 16 }}>
          What We Do
        </div>
        <h2 style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 800, marginBottom: 48, maxWidth: 560 }}>
          Every Letter. Every Round. Every Bureau.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 1, background: 'rgba(201,168,76,0.08)' }}>
          {[
            { icon: '📋', title: 'Bureau Dispute Letters', desc: 'FCRA §611 disputes to Experian, Equifax, and TransUnion with Metro 2 non-compliance grounds and breach context.' },
            { icon: '📜', title: 'Affidavit of Truth', desc: 'Sworn testimony under 28 U.S.C. §1746 — forces CRA legal department review instead of e-OSCAR automation.' },
            { icon: '⚖', title: 'Debt Collector Letters', desc: 'FDCPA §1692c cease & desist, §1692g validation demands, and credit reporting as communication notices.' },
            { icon: '🏛', title: 'CFPB Complaints', desc: 'Formal regulatory complaints with documented enforcement action history and 6-item resolution demands.' },
            { icon: '🔍', title: 'Failure to Investigate', desc: 'Escalation letters citing Cushman v. Trans Union when bureaus parrot furnisher data without genuine reinvestigation.' },
            { icon: '✍️', title: 'Authorization & Disclosure', desc: 'Power of attorney and full file disclosure requests so we can act on your behalf with any party.' },
          ].map(s => (
            <div key={s.title} style={{ background: '#0c1018', padding: '32px 28px' }}>
              <div style={{ fontSize: 28, marginBottom: 14 }}>{s.icon}</div>
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10, color: '#e8eaf0' }}>{s.title}</h3>
              <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.7 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section style={{ padding: '80px 48px', textAlign: 'center' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 16 }}>
          Simple Pricing
        </div>
        <h2 style={{ fontSize: 'clamp(24px, 3vw, 40px)', fontWeight: 800, marginBottom: 12 }}>
          One Flat Rate. No Surprises.
        </h2>
        <p style={{ color: '#64748b', fontSize: 16, marginBottom: 48 }}>
          Cancel anytime — required by the Credit Repair Organizations Act (15 U.S.C. §1679b).
        </p>
        <div style={{
          display: 'inline-block', background: '#0c1018',
          border: '1px solid rgba(201,168,76,0.2)', borderRadius: 12,
          padding: '40px 56px', maxWidth: 440,
        }}>
          <div style={{ fontSize: 48, fontWeight: 900, color: '#c9a84c' }}>
            $149<span style={{ fontSize: 18, color: '#64748b', fontWeight: 400 }}>/month</span>
          </div>
          <div style={{ fontSize: 13, color: '#64748b', margin: '8px 0 28px' }}>Monthly Consulting Retainer</div>
          {[
            'Unlimited dispute letters',
            'All three credit bureaus',
            'Debt collector correspondence',
            'CFPB complaint preparation',
            'Document portal access',
            'Ongoing FCRA/FDCPA advisory',
          ].map(f => (
            <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, textAlign: 'left' }}>
              <span style={{ color: '#c9a84c', fontWeight: 700 }}>✓</span>
              <span style={{ fontSize: 14, color: '#e8eaf0' }}>{f}</span>
            </div>
          ))}
          <a href="/portal/register" style={{
            display: 'block', marginTop: 28, padding: '14px 0',
            background: '#c9a84c', color: '#07090f', fontWeight: 800,
            fontSize: 15, borderRadius: 6, textDecoration: 'none',
          }}>
            Start Today →
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        background: '#0c1018', borderTop: '1px solid rgba(201,168,76,0.1)',
        padding: '40px 48px', display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', flexWrap: 'wrap', gap: 16,
      }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#c9a84c', letterSpacing: 1 }}>CRUEL & ASSOCIATES</div>
          <div style={{ fontSize: 11, color: '#4a5060', marginTop: 4 }}>Consumer Rights Consulting · (864) 318-9951 · yueseyuan.cruel@cruelandassociates.site</div>
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: '#64748b' }}>
          <a href="/portal/login" style={{ color: '#64748b', textDecoration: 'none' }}>Client Portal</a>
          <a href="/portal/register" style={{ color: '#c9a84c', textDecoration: 'none', fontWeight: 600 }}>Get Started</a>
        </div>
      </footer>
    </div>
  );
}
