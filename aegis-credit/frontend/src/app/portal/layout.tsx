'use client';
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getPortalToken, getPortalRole, clearPortalAuth } from '@/lib/portal-api';

const STAFF_ROLES = ['admin', 'investigator', 'reviewer', 'readonly'];

const PUBLIC_PATHS = ['/portal/login', '/portal/register'];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getPortalToken();
    const role = getPortalRole();
    const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p));

    if (!token && !isPublic) {
      router.replace('/portal/login');
      return;
    }
    // Staff token landed on the portal — clear it so they can log in as a client.
    if (token && role && STAFF_ROLES.includes(role) && isPublic) {
      clearPortalAuth();
      setReady(true);
      return;
    }
    if (token && role === 'client' && isPublic) {
      router.replace('/portal/dashboard');
      return;
    }
    setReady(true);
  }, [pathname, router]);

  const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p));

  function handleLogout() {
    clearPortalAuth();
    router.push('/portal/login');
  }

  if (!ready) return null;

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fa', fontFamily: 'system-ui, sans-serif' }}>
      {!isPublic && (
        <header style={{
          background: '#0a2540',
          color: '#fff',
          padding: '0 24px',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 22 }}>⚖</span>
            <span style={{ fontWeight: 700, fontSize: 16, letterSpacing: 0.3 }}>
              Cruel &amp; Associates — Client Portal
            </span>
          </div>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 24, fontSize: 14 }}>
            <a href="/portal/dashboard" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Dashboard</a>
            <a href="/portal/profile" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Profile</a>
            <a href="/portal/documents" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Documents</a>
            <a href="/portal/letters" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Letters</a>
            <a href="/portal/disputes" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Disputes</a>
            <a href="/portal/billing" style={{ color: '#ccd6f6', textDecoration: 'none' }}>Billing</a>
            <button
              onClick={handleLogout}
              style={{
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.3)',
                color: '#ccd6f6',
                padding: '5px 14px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              Sign Out
            </button>
          </nav>
        </header>
      )}
      <main style={{ maxWidth: 900, margin: '0 auto', padding: isPublic ? 0 : '32px 24px' }}>
        {children}
      </main>
    </div>
  );
}
