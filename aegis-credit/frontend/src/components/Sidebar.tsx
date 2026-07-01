'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { clearToken, globalSearch } from '@/lib/api';

interface SearchResult { id: number; name?: string; case_number?: string; creditor_name?: string; type: string; client_id?: number; case_id?: number; bureau?: string; status?: string; }

const NAV_SECTIONS = [
  {
    section: 'Investigation',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: '◼' },
      { href: '/cases', label: 'Credit Cases', icon: '📁' },
      { href: '/clients', label: 'Clients', icon: '👥' },
      { href: '/analytics', label: 'Analytics', icon: '📊' },
    ],
  },
  {
    section: 'Services',
    items: [
      { href: '/services', label: 'All Services', icon: '🏛' },
      { href: '/services/notary', label: 'Mobile Notary', icon: '✍️' },
      { href: '/services/criminal', label: 'Record Relief', icon: '📋' },
      { href: '/services/document', label: 'Doc Preparation', icon: '📄' },
      { href: '/services/judgment', label: 'Asset Recovery', icon: '⚖️' },
      { href: '/services/consulting', label: 'Consulting', icon: '💼' },
    ],
  },
  {
    section: 'Operations',
    items: [
      { href: '/appointments', label: 'Appointments', icon: '📅' },
      { href: '/invoices', label: 'Invoices', icon: '💵' },
      { href: '/templates', label: 'Templates', icon: '📝' },
    ],
  },
  {
    section: 'Research',
    items: [
      { href: '/legal', label: 'Legal Knowledge', icon: '⚖' },
      { href: '/learning', label: 'Learning Vault', icon: '🧠' },
    ],
  },
  {
    section: 'Administration',
    items: [
      { href: '/admin/portal', label: 'Portal Intake', icon: '📥' },
      { href: '/organizations', label: 'Organizations', icon: '🏢' },
      { href: '/admin/users', label: 'User Management', icon: '👤' },
      { href: '/admin/legal-updates', label: 'Legal Updates', icon: '📰' },
      { href: '/admin/audit', label: 'Audit Log', icon: '🔍' },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<{clients: SearchResult[], cases: SearchResult[], tradelines: SearchResult[]} | null>(null);
  const [searching, setSearching] = useState(false);

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

      {/* Search bar */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', position: 'relative' }}>
        <input
          type="text"
          placeholder="Search..."
          value={query}
          onChange={e => {
            setQuery(e.target.value);
            if (e.target.value.length >= 2) {
              setSearching(true);
              globalSearch(e.target.value).then(r => { setResults(r); setSearching(false); }).catch(() => setSearching(false));
            } else {
              setResults(null);
            }
          }}
          style={{ width: '100%', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 6, padding: '6px 10px', color: '#fff', fontSize: 13, boxSizing: 'border-box' }}
        />
        {results && (results.clients.length > 0 || results.cases.length > 0 || results.tradelines.length > 0) && (
          <div style={{ position: 'absolute', left: 12, right: 12, top: 46, background: '#1e293b', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 6, zIndex: 100, maxHeight: 280, overflowY: 'auto' }}>
            {results.clients.map(r => (
              <Link key={`c${r.id}`} href={`/clients/${r.id}`} onClick={() => { setQuery(''); setResults(null); }}
                style={{ display: 'block', padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 12, color: '#e2e8f0' }}>
                👤 {r.name}
              </Link>
            ))}
            {results.cases.map(r => (
              <Link key={`ca${r.id}`} href={`/cases/${r.id}`} onClick={() => { setQuery(''); setResults(null); }}
                style={{ display: 'block', padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 12, color: '#e2e8f0' }}>
                📁 Case {r.case_number} <span style={{ color: 'rgba(255,255,255,0.4)' }}>({r.status})</span>
              </Link>
            ))}
            {results.tradelines.map(r => (
              <Link key={`t${r.id}`} href={`/cases/${r.case_id}/tradelines`} onClick={() => { setQuery(''); setResults(null); }}
                style={{ display: 'block', padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 12, color: '#e2e8f0' }}>
                💳 {r.creditor_name} <span style={{ color: 'rgba(255,255,255,0.4)' }}>({r.bureau})</span>
              </Link>
            ))}
          </div>
        )}
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
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Link href="/profile" style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', textDecoration: 'none' }}>
          ⚙ Profile
        </Link>
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
