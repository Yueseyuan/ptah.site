'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

const PUBLIC_PATHS = [
  '/judgment-portal',
  '/judgment-portal/login',
  '/judgment-portal/register',
];

export function getJudgmentToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('judgment_token');
}
export function clearJudgmentAuth() {
  localStorage.removeItem('judgment_token');
  localStorage.removeItem('judgment_role');
}

export default function JudgmentPortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  const isPublic = PUBLIC_PATHS.some(p => pathname === p || (pathname.startsWith(p + '/') && p !== '/judgment-portal')) || pathname === '/judgment-portal';

  useEffect(() => {
    const token = getJudgmentToken();
    if (!token && !isPublic) {
      router.replace('/judgment-portal/login');
      return;
    }
    setReady(true);
  }, [pathname, router, isPublic]);

  function handleLogout() {
    clearJudgmentAuth();
    router.push('/judgment-portal/login');
  }

  if (!ready) return null;

  const showNav = !isPublic;

  return (
    <div style={{ minHeight: '100vh', background: '#f0f4f8', fontFamily: 'system-ui, sans-serif' }}>
      {showNav && (
        <header style={{
          background: '#1c1917', color: '#fff', padding: '0 28px',
          height: 56, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100,
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          borderBottom: '1px solid rgba(201,168,76,0.2)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>⚖️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: 0.2 }}>Cruel &amp; Associates — Recovery Portal</div>
              <div style={{ fontSize: 10, color: '#C9A84C', letterSpacing: 1, textTransform: 'uppercase' }}>Judgment &amp; Asset Recovery</div>
            </div>
          </div>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 24, fontSize: 13 }}>
            <a href="/judgment-portal/dashboard" style={{ color: '#d6d3d1', textDecoration: 'none' }}>My Cases</a>
            <a href="/judgment-portal/intake" style={{ color: '#d6d3d1', textDecoration: 'none' }}>New Case</a>
            <button onClick={handleLogout} style={{
              background: 'transparent', border: '1px solid rgba(255,255,255,0.25)',
              color: '#d6d3d1', padding: '5px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
            }}>Sign Out</button>
          </nav>
        </header>
      )}
      <main style={{ maxWidth: 900, margin: '0 auto', padding: showNav ? '32px 24px' : 0 }}>
        {children}
      </main>
    </div>
  );
}
