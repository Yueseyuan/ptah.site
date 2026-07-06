'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listClients } from '@/lib/api';

interface Client { id: number; first_name: string; last_name: string; email: string; phone: string; state: string; created_at: string; }

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    listClients().then(setClients).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const q = search.toLowerCase().trim();
  const visible = q
    ? clients.filter(c =>
        `${c.first_name} ${c.last_name}`.toLowerCase().includes(q) ||
        (c.email || '').toLowerCase().includes(q) ||
        (c.state || '').toLowerCase().includes(q) ||
        (c.phone || '').includes(q)
      )
    : clients;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Clients</h1>
            <p>{visible.length} of {clients.length} client{clients.length !== 1 ? 's' : ''}</p>
          </div>
          <Link href="/clients/new" className="btn btn-primary">+ New Client</Link>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <input
            type="text"
            placeholder="Search by name, email, phone, or state…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13 }}
          />
        </div>

        <div className="card">
          {loading ? <div className="spinner" /> : visible.length === 0 ? (
            <p className="empty">
              {clients.length === 0
                ? <><span>No clients yet. </span><Link href="/clients/new">Add one.</Link></>
                : 'No clients match your search.'}
            </p>
          ) : (
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>State</th><th>Added</th><th></th></tr></thead>
              <tbody>
                {visible.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}><Link href={`/clients/${c.id}`}>{c.first_name} {c.last_name}</Link></td>
                    <td>{c.email || '—'}</td>
                    <td>{c.phone || '—'}</td>
                    <td>{c.state || '—'}</td>
                    <td style={{ color: 'var(--muted)' }}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td><Link href={`/clients/${c.id}`} className="btn btn-outline btn-sm">View</Link></td>
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
