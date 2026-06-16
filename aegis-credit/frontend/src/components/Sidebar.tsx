'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { clearToken } from '@/lib/api';

const NAV_SECTIONS = [
  {
    section: 'Investigation',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: '◼' },
      { href: '/cases', label: 'Cases', icon: '📁' },
      { href: '/clients', label: 'Clients', icon: '👥' },
    ],
  },
  {
    section: 'Research',
    items: [
      { href: '/legal', label: 'Legal Knowledge', icon: '⚖' },
    ],
  },
  {
    section: 'Knowledge',
    items: [
      { href: '/learning', label: 'Learning Vault', icon: '🧠' },
    ],
  },
  {
    section: 'Administration',
    items: [
      { href: '/organizations', label: 'Organizations', icon: '🏢' },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push('/login');
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>Aegis</h2>
        <p>Credit Investigator</p>
      </div>
      <nav style={{ flex: 1 }}>
        {NAV_SECTIONS.map(({ section, items }) => (
          <div key={section}>
            <div className="sidebar-section">{section}</div>
            {items.map((n) => {
              const isActive = n.href === '/dashboard'
                ? path === '/dashboard'
                : path.startsWith(n.href);
              return (
                <Link key={n.href} href={n.href} className={isActive ? 'active' : ''}>
                  <span className="sidebar-icon">{n.icon}</span>
                  {n.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <button
          onClick={handleLogout}
          style={{
            background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
            cursor: 'pointer', fontSize: 12, padding: 0,
          }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
