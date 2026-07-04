'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import api from '@/lib/api';

interface ServiceCase {
  id: number;
  case_number: string;
  client_name: string;
  status: string;
  created_at: string;
  division: string;
}

const DIVISION_META: Record<string, { name: string; icon: string; description: string }> = {
  notary: {
    name: 'Mobile Notary',
    icon: '✍️',
    description: 'Signing services, travel coordination, and notary journal management.',
  },
  credit: {
    name: 'Credit Restoration',
    icon: '💳',
    description: 'Credit investigation, dispute management, and score improvement.',
  },
  criminal: {
    name: 'Criminal Record Relief',
    icon: '📋',
    description: 'Expungements, pardons, record sealing, and reentry assistance.',
  },
  document: {
    name: 'Document Preparation',
    icon: '📄',
    description: 'Affidavits, contracts, demand letters, and legal document preparation.',
  },
  judgment: {
    name: 'Judgment & Asset Recovery',
    icon: '⚖️',
    description: 'Asset searches, judgment enforcement, and surplus funds recovery.',
  },
  consulting: {
    name: 'Business Consulting',
    icon: '💼',
    description: 'LLC formation, business plans, and standard operating procedures.',
  },
  overages: {
    name: 'Tax Overage Recovery',
    icon: '🏛️',
    description: 'Tax deed surplus fund recovery — contingency claims for former property owners.',
  },
};

const STATUS_COLORS: Record<string, string> = {
  intake: '#3b82f6',
  active: '#10b981',
  on_hold: '#f59e0b',
  closed: '#6b7280',
};

const STATUS_TABS = ['all', 'intake', 'active', 'on_hold', 'closed'];

export default function DivisionPage() {
  const { division } = useParams<{ division: string }>();
  const [cases, setCases] = useState<ServiceCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const meta = DIVISION_META[division] || {
    name: division.charAt(0).toUpperCase() + division.slice(1),
    icon: '📁',
    description: '',
  };

  useEffect(() => {
    if (!division) return;
    setLoading(true);
    api.get<ServiceCase[]>(`/api/service-cases`, { params: { division } })
      .then(r => setCases(r.data))
      .catch(e => setError(e.message || 'Failed to load cases.'))
      .finally(() => setLoading(false));
  }, [division]);

  const visible = statusFilter === 'all'
    ? cases
    : cases.filter(c => c.status === statusFilter);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 32 }}>{meta.icon}</span>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Link href="/services" style={{ fontSize: 12, color: 'var(--muted)', textDecoration: 'none' }}>
                  Services
                </Link>
                <span style={{ color: 'var(--muted)', fontSize: 12 }}>/</span>
                <h1 style={{ margin: 0 }}>{meta.name}</h1>
              </div>
              <p>{meta.description}</p>
            </div>
          </div>
          <Link href={`/services/${division}/new`} className="btn btn-primary">
            + New Case
          </Link>
        </div>

        {/* Status filter tabs */}
        <div className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {STATUS_TABS.map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={statusFilter === s ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}
              >
                {s === 'all' ? 'All' : s.replace('_', ' ')}
                {s === 'all' && !loading && (
                  <span style={{ marginLeft: 4, opacity: 0.7 }}>({cases.length})</span>
                )}
                {s !== 'all' && !loading && (
                  <span style={{ marginLeft: 4, opacity: 0.7 }}>
                    ({cases.filter(c => c.status === s).length})
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Cases table */}
        <div className="card">
          {error && <div className="alert-error">{error}</div>}
          {loading ? (
            <div className="spinner" />
          ) : visible.length === 0 ? (
            <p className="empty">
              {cases.length === 0 ? (
                <>
                  <span>No cases in this division yet. </span>
                  <Link href={`/services/${division}/new`}>Create the first one.</Link>
                </>
              ) : (
                'No cases match the selected status.'
              )}
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Case #</th>
                  <th>Client</th>
                  <th>Status</th>
                  <th>Opened</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visible.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>
                      <Link href={`/services/${division}/${c.id}`}>
                        <code>{c.case_number}</code>
                      </Link>
                    </td>
                    <td>{c.client_name || '—'}</td>
                    <td>
                      <span style={{
                        background: STATUS_COLORS[c.status] || '#999',
                        color: 'white',
                        borderRadius: 4,
                        padding: '2px 8px',
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {c.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <Link href={`/services/${division}/${c.id}`} className="btn btn-outline btn-sm">
                        View
                      </Link>
                      <Link href={`/services/${division}/${c.id}?tab=overview`} className="btn btn-outline btn-sm">
                        Edit
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
