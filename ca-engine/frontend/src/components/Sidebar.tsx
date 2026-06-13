'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { href: '/clients', label: 'Clients', icon: '👥' },
  { href: '/cases', label: 'Cases', icon: '📁' },
  { href: '/documents', label: 'Documents', icon: '📄' },
  { href: '/appointments', label: 'Appointments', icon: '📅' },
  { href: '/invoices', label: 'Invoices', icon: '💰' },
  { href: '/notary', label: 'Notary Log', icon: '✍️' },
  { href: '/admin', label: 'Admin', icon: '⚙️' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    localStorage.removeItem('ca_token');
    localStorage.removeItem('ca_user');
    router.push('/login');
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>Cruel & Associates</h2>
        <p>CA Engine v1.0</p>
      </div>
      <nav style={{ marginTop: 8 }}>
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={pathname.startsWith(item.href) ? 'active' : ''}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, padding: '0 20px' }}>
        <button
          onClick={handleLogout}
          style={{
            width: '100%', padding: '9px', background: 'rgba(255,255,255,0.1)',
            border: 'none', borderRadius: 6, color: 'rgba(255,255,255,0.7)',
            fontSize: 13, cursor: 'pointer',
          }}
        >
          Sign Out
        </button>
      </div>
    </aside>
  );
}
