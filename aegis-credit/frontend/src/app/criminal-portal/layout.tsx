'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

const STORAGE_KEY = 'criminal_token';

export function getCriminalToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function clearCriminalAuth() {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem('criminal_role');
}

const PUBLIC_PATHS = [
  '/criminal-portal',
  '/criminal-portal/login',
  '/criminal-portal/register',
];

export default function CriminalPortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  const isPublic = PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/') && p !== '/criminal-portal') || pathname === '/criminal-portal';

  useEffect(() => {
    const token = getCriminalToken();
    if (!token && !isPublic) {
      router.replace('/criminal-portal/login');
      return;
    }
    setReady(true);
  }, [pathname, router, isPublic]);

  function handleLogout() {
    clearCriminalAuth();
    router.push('/criminal-portal/login');
  }

  if (!ready) return null;

  const showNav = !isPublic;

  return (
    <div style={{ minHeight: '100vh', background: '#f0f4f8', fontFamily: 'system-ui, sans-serif' }}>
      {showNav && (
        <header style={{
          background: '#1a1a2e', color: '#fff', padding: '0 28px',
          height: 56, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100,
          boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>⚖️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: 0.2 }}>Cruel &amp; Associates — Record Relief</div>
              <div style={{ fontSize: 10, color: '#a78bfa', letterSpacing: 1, textTransform: 'uppercase' }}>Criminal Relief Portal</div>
            </div>
          </div>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 24, fontSize: 13 }}>
            <a href="/criminal-portal/dashboard" style={{ color: '#c4b5fd', textDecoration: 'none' }}>My Cases</a>
            <button onClick={handleLogout} style={{
              background: 'transparent', border: '1px solid rgba(255,255,255,0.3)',
              color: '#c4b5fd', padding: '5px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
            }}>Sign Out</button>
          </nav>
        </header>
      )}
      <main style={{ maxWidth: 860, margin: '0 auto', padding: showNav ? '32px 24px' : 0 }}>
        {children}
      </main>
    </div>
  );
}
