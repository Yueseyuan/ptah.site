'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listClients } from '@/lib/api';

interface Client { id: number; first_name: string; last_name: string; email: string; phone: string; state: string; created_at: string; }

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listClients().then(setClients).finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Clients</h1><p>{clients.length} total clients</p></div>
          <Link href="/clients/new" className="btn btn-primary">+ New Client</Link>
        </div>
        <div className="card">
          {loading ? <div className="spinner" /> : clients.length === 0 ? (
            <p className="empty">No clients yet. <Link href="/clients/new">Add one.</Link></p>
          ) : (
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>State</th><th>Added</th><th></th></tr></thead>
              <tbody>
                {clients.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}><Link href={`/clients/${c.id}`}>{c.first_name} {c.last_name}</Link></td>
                    <td>{c.email || '—'}</td>
                    <td>{c.phone || '—'}</td>
                    <td>{c.state}</td>
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
