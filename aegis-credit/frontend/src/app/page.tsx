export default function HomePage() {
  const SERVICES = [
    {
      icon: '📑',
      tag: 'Credit Services',
      title: 'Credit Repair & Consumer Rights',
      desc: 'FCRA & FDCPA dispute correspondence — bureau letters, debt-collector cease & desist, CFPB complaints, and affidavits of truth. Flat monthly retainer, no hourly billing.',
      cta: 'Start Your Case →',
      href: '/portal/register?service=credit',
      primary: true,
      detail: ['Bureau dispute letters (all 3)', 'Debt collector C&D', 'CFPB complaints', 'Affidavit of Truth', '$149/month flat'],
    },
    {
      icon: '🛡️',
      tag: 'Record Relief',
      title: 'Criminal Record Relief',
      desc: 'Document preparation for expungements, record sealings, and post-conviction relief. We handle the paperwork — you move forward with a clean slate.',
      cta: 'Request Intake →',
      href: '/portal/criminal',
      primary: true,
      detail: ['Expungement petitions', 'Record sealing', 'Pardons & post-conviction', 'Eligibility pre-check', 'Court filing support'],
    },
    {
      icon: '📋',
      tag: 'Doc Prep',
      title: 'Document Preparation',
      desc: 'Legal and business documents prepared accurately and ready to sign — LLC formations, operating agreements, demand letters, leases, POA, and custom contracts.',
      cta: 'Request Documents →',
      href: '/portal/doc-prep',
      primary: true,
      detail: ['LLC formation', 'Operating agreements', 'Demand letters', 'Power of attorney', 'Lease agreements'],
    },
    {
      icon: '💼',
      tag: 'Business',
      title: 'Business Consulting',
      desc: 'Practical advisory for small and mid-sized businesses — entity formation, compliance, business credit building, and growth strategy tailored to where you are right now.',
      cta: 'Book Consultation →',
      href: '/portal/consulting',
      primary: true,
      detail: ['Entity formation', 'Business credit building', 'Compliance advisory', '90-day growth plan', 'Ongoing advisory'],
    },
    {
      icon: '🖊️',
      tag: 'Notary',
      title: 'Mobile Notary Services',
      desc: 'Certified mobile notary for loan signings, real estate closings, affidavits, and powers of attorney — at a location convenient for you.',
      cta: 'Schedule Signing →',
      href: '/portal/book',
      primary: false,
      detail: ['Loan closings', 'Real estate signings', 'Affidavits', 'POA notarization', 'RON available'],
    },
  ];

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
        background: 'rgba(7,9,15,0.94)', backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(201,168,76,0.12)',
      }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#c9a84c', letterSpacing: 1 }}>
            CRUEL &amp; ASSOCIATES
          </div>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 3, textTransform: 'uppercase', marginTop: 2 }}>
            Consumer Rights &amp; Business Services
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <a href="/login" style={{ fontSize: 11, color: '#4a5060', textDecoration: 'none', letterSpacing: 0.5 }}>
            Staff
          </a>
          <a href="/portal/login" style={{
            padding: '8px 20px', border: '1px solid rgba(201,168,76,0.4)',
            color: '#c9a84c', borderRadius: 4, fontSize: 13, fontWeight: 600,
            textDecoration: 'none',
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
          Credit · Record Relief · Doc Prep · Business · Notary
        </div>

        <h1 style={{
          fontSize: 'clamp(36px, 6vw, 80px)', fontWeight: 900,
          lineHeight: 1.05, letterSpacing: -2, maxWidth: 820, margin: '0 0 24px',
        }}>
          Your Rights. Your Records.<br />
          <span style={{
            background: 'linear-gradient(135deg, #c9a84c, #e6c96e)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            Your Future.
          </span>
        </h1>

        <p style={{
          fontSize: 18, color: '#8a90a0', lineHeight: 1.8,
          maxWidth: 560, fontWeight: 300, marginBottom: 40,
        }}>
          From credit disputes to expungements, document preparation to business growth —
          we give you the tools and advocacy to move forward on every front.
        </p>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <a href="/portal/register" style={{
            padding: '15px 36px', background: '#c9a84c', color: '#07090f',
            fontWeight: 800, fontSize: 15, borderRadius: 4, textDecoration: 'none',
          }}>
            Open a Case →
          </a>
          <a href="/portal/login" style={{
            padding: '15px 36px', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.15)', color: '#e8eaf0',
            fontSize: 15, borderRadius: 4, textDecoration: 'none',
          }}>
            Client Portal
          </a>
        </div>

        <div style={{
          display: 'flex', gap: 48, marginTop: 72,
          paddingTop: 40, borderTop: '1px solid rgba(201,168,76,0.12)',
          flexWrap: 'wrap',
        }}>
          {[
            { num: '5', suffix: ' services', label: 'Credit · Relief · Docs · Biz · Notary' },
            { num: '$1,000', suffix: '', label: 'Statutory Damages per FDCPA Violation' },
            { num: '30', suffix: ' days', label: 'Bureau Response Window (FCRA §611)' },
            { num: '$149', suffix: '/mo', label: 'Credit Repair Flat Retainer' },
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

      {/* Services Grid */}
      <section style={{ padding: '80px 48px', background: '#07090f' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 16 }}>
          Our Services
        </div>
        <h2 style={{ fontSize: 'clamp(24px, 3vw, 42px)', fontWeight: 800, marginBottom: 16, maxWidth: 640 }}>
          Five Ways We Help You Get Ahead
        </h2>
        <p style={{ color: '#64748b', fontSize: 16, marginBottom: 56, maxWidth: 540 }}>
          Each service has its own dedicated portal page. Click into the one that fits your situation and start the intake process today.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
          {SERVICES.map(s => (
            <div key={s.title} style={{
              background: '#0c1018',
              border: `1px solid ${s.primary ? 'rgba(201,168,76,0.28)' : 'rgba(201,168,76,0.12)'}`,
              borderRadius: 10, padding: '32px 28px',
              display: 'flex', flexDirection: 'column',
              position: 'relative',
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 18 }}>
                <span style={{ fontSize: 34 }}>{s.icon}</span>
                <span style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: 2,
                  color: '#c9a84c', textTransform: 'uppercase',
                  background: 'rgba(201,168,76,0.08)',
                  border: '1px solid rgba(201,168,76,0.2)',
                  padding: '3px 10px', borderRadius: 12,
                }}>
                  {s.tag}
                </span>
              </div>
              <h3 style={{ fontSize: 19, fontWeight: 800, color: '#e8eaf0', marginBottom: 12, lineHeight: 1.2 }}>
                {s.title}
              </h3>
              <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.75, marginBottom: 20, flex: 1 }}>
                {s.desc}
              </p>
              <ul style={{ margin: '0 0 24px', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {s.detail.map(d => (
                  <li key={d} style={{ fontSize: 12, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ color: '#c9a84c', fontSize: 10, fontWeight: 700 }}>›</span>
                    {d}
                  </li>
                ))}
              </ul>
              <a href={s.href} style={{
                display: 'block', padding: '11px 20px',
                background: s.primary ? '#c9a84c' : 'transparent',
                color: s.primary ? '#07090f' : '#c9a84c',
                border: s.primary ? 'none' : '1px solid rgba(201,168,76,0.4)',
                fontWeight: 700, fontSize: 13, borderRadius: 5,
                textDecoration: 'none', textAlign: 'center',
              }}>
                {s.cta}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Credit Repair Detail */}
      <section style={{ padding: '80px 48px', background: '#0c1018' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 3, color: '#c9a84c', textTransform: 'uppercase', marginBottom: 16 }}>
          Credit Repair — What We Do
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
          Credit Repair Pricing
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
          <a href="/portal/register?service=credit" style={{
            display: 'block', marginTop: 28, padding: '14px 0',
            background: '#c9a84c', color: '#07090f', fontWeight: 800,
            fontSize: 15, borderRadius: 6, textDecoration: 'none',
          }}>
            Start Today →
          </a>
        </div>
        <p style={{ marginTop: 28, fontSize: 13, color: '#4a5060' }}>
          Other services are quoted per-project. Contact us or use the service pages above.
        </p>
      </section>

      {/* Footer */}
      <footer style={{
        background: '#0c1018', borderTop: '1px solid rgba(201,168,76,0.1)',
        padding: '40px 48px', display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', flexWrap: 'wrap', gap: 16,
      }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#c9a84c', letterSpacing: 1 }}>CRUEL &amp; ASSOCIATES</div>
          <div style={{ fontSize: 11, color: '#4a5060', marginTop: 4 }}>Consumer Rights Consulting · (864) 318-9951 · yueseyuan.cruel@cruelandassociates.site</div>
        </div>
        <div style={{ display: 'flex', gap: 20, fontSize: 13, color: '#64748b', flexWrap: 'wrap', alignItems: 'center' }}>
          <a href="/portal/criminal" style={{ color: '#64748b', textDecoration: 'none' }}>Record Relief</a>
          <a href="/portal/doc-prep" style={{ color: '#64748b', textDecoration: 'none' }}>Doc Prep</a>
          <a href="/portal/consulting" style={{ color: '#64748b', textDecoration: 'none' }}>Consulting</a>
          <a href="/portal/login" style={{ color: '#64748b', textDecoration: 'none' }}>Client Portal</a>
          <a href="/portal/register" style={{ color: '#c9a84c', textDecoration: 'none', fontWeight: 600 }}>Get Started</a>
          <a href="/login" style={{ color: '#374151', textDecoration: 'none', fontSize: 11, opacity: 0.5 }}>Staff</a>
        </div>
      </footer>
    </div>
  );
}
