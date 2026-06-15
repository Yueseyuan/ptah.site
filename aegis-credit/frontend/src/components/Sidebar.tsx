'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/cases', label: 'Cases', icon: '📁' },
  { href: '/clients', label: 'Clients', icon: '👥' },
  { href: '/learning', label: 'Learning Vault', icon: '🧠' },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>Aegis</h2>
        <p>Credit Investigator</p>
      </div>
      <nav>
        <div className="sidebar-section">Navigation</div>
        {NAV.map((n) => (
          <Link key={n.href} href={n.href}
            className={path.startsWith(n.href) ? 'active' : ''}>
            <span className="sidebar-icon">{n.icon}</span>
            {n.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
