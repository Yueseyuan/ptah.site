'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getNotaryToken, clearNotaryAuth } from '@/lib/notary-api';

const PUBLIC_PATHS = [
  '/notary-portal',
  '/notary-portal/login',
  '/notary-portal/register',
  '/notary-portal/client',
];

export default function NotaryPortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  const isPublic = PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/') && p !== '/notary-portal') || pathname === '/notary-portal';

  useEffect(() => {
    const token = getNotaryToken();
    if (!token && !isPublic) {
      router.replace('/notary-portal/login');
      return;
    }
    setReady(true);
  }, [pathname, router, isPublic]);

  function handleLogout() {
    clearNotaryAuth();
    router.push('/notary-portal/login');
  }

  if (!ready) return null;

  const showNav = !isPublic;

  return (
    <div style={{ minHeight: '100vh', background: '#f0f4f8', fontFamily: 'system-ui, sans-serif' }}>
      {showNav && (
        <header style={{
          background: '#0f2d52', color: '#fff', padding: '0 28px',
          height: 56, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100,
          boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 22 }}>🖊️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: 0.2 }}>Cruel &amp; Associates — Notary Portal</div>
              <div style={{ fontSize: 10, color: '#93c5fd', letterSpacing: 1, textTransform: 'uppercase' }}>Professional Dashboard</div>
            </div>
          </div>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 24, fontSize: 13 }}>
            <a href="/notary-portal/dashboard" style={{ color: '#ccd6f6', textDecoration: 'none' }}>My Orders</a>
            <button onClick={handleLogout} style={{
              background: 'transparent', border: '1px solid rgba(255,255,255,0.3)',
              color: '#ccd6f6', padding: '5px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
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
