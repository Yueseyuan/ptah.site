'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';

interface DivisionStats {
  division: string;
  count: number;
}

const DIVISIONS = [
  {
    slug: 'notary',
    icon: '✍️',
    name: 'Mobile Notary',
    description: 'Signing services, travel coordination, and journal management for mobile notary appointments.',
  },
  {
    slug: 'credit',
    icon: '💳',
    name: 'Credit Restoration',
    description: 'Full credit investigation and dispute management. Already tracked in Aegis.',
    href: '/cases',
  },
  {
    slug: 'criminal',
    icon: '📋',
    name: 'Criminal Record Relief',
    description: 'Reentry assistance including expungements, pardons, and record sealing services.',
  },
  {
    slug: 'document',
    icon: '📄',
    name: 'Document Preparation',
    description: 'Preparation of affidavits, contracts, demand letters, and other legal documents.',
  },
  {
    slug: 'judgment',
    icon: '⚖️',
    name: 'Judgment & Asset Recovery',
    description: 'Asset searches, judgment enforcement, and surplus funds recovery services.',
  },
  {
    slug: 'consulting',
    icon: '💼',
    name: 'Business Consulting',
    description: 'LLC formation, business planning, and standard operating procedure development.',
  },
  {
    slug: 'overages',
    icon: '🏛️',
    name: 'Tax Overage Recovery',
    description: 'Tax deed surplus fund recovery — locate former owners and file contingency claims on excess proceeds.',
  },
];

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6',
  active: '#10b981',
  on_hold: '#f59e0b',
  closed: '#6b7280',
};

export default function ServicesPage() {
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<DivisionStats[]>('/api/service-cases/divisions')
      .then(r => {
        const m: Record<string, number> = {};
        for (const d of r.data) m[d.division] = d.count;
        setStats(m);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Services</h1>
          <p>All service divisions managed by Aegis</p>
        </div>

        {/* Quick stats row */}
        <div className="stat-grid" style={{ marginBottom: 28 }}>
          {DIVISIONS.map(d => (
            <div key={d.slug} className="stat-card">
              <div className="label">{d.name}</div>
              <div className="value" style={{ fontSize: 22 }}>
                {loading ? '—' : (stats[d.slug] ?? 0)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>cases</div>
            </div>
          ))}
        </div>

        {/* Division cards grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 16,
        }}>
          {DIVISIONS.map(d => (
            <div key={d.slug} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 28 }}>{d.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--navy)' }}>{d.name}</div>
                  {!loading && (
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                      {stats[d.slug] ?? 0} case{(stats[d.slug] ?? 0) !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
              <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.5, flex: 1 }}>
                {d.description}
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                {d.href ? (
                  <Link href={d.href} className="btn btn-primary btn-sm">
                    View Cases
                  </Link>
                ) : (
                  <Link href={`/services/${d.slug}`} className="btn btn-primary btn-sm">
                    View Cases
                  </Link>
                )}
                {!d.href && (
                  <Link href={`/services/${d.slug}/new`} className="btn btn-outline btn-sm">
                    + New Case
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
