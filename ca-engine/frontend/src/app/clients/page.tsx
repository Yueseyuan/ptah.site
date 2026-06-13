'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { listClients } from '@/lib/api';

interface Client {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
}

export default function ClientsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem('ca_token')) { router.push('/login'); return; }
    loadClients();
  }, []);

  async function loadClients(q?: string) {
    setLoading(true);
    try {
      const data = await listClients(q);
      setClients(data);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    loadClients(search);
  }

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Clients</h1>
            <p>Manage client records across all divisions</p>
          </div>
          <Link href="/clients/new" className="btn btn-primary">+ New Client</Link>
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10 }}>
            <input
              placeholder="Search by name, email, or phone…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-primary">Search</button>
            {search && (
              <button type="button" className="btn btn-outline" onClick={() => { setSearch(''); loadClients(); }}>
                Clear
              </button>
            )}
          </form>
        </div>

        <div className="card">
          {loading ? (
            <div className="spinner" />
          ) : clients.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
              No clients found. <Link href="/clients/new">Add the first one.</Link>
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Location</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {clients.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>
                      <Link href={`/clients/${c.id}`}>{c.first_name} {c.last_name}</Link>
                    </td>
                    <td>{c.email || '—'}</td>
                    <td>{c.phone || '—'}</td>
                    <td>{[c.city, c.state].filter(Boolean).join(', ') || '—'}</td>
                    <td>
                      <Link href={`/clients/${c.id}`} className="btn btn-outline btn-sm">View</Link>
                      {' '}
                      <Link href={`/cases/new?client_id=${c.id}`} className="btn btn-gold btn-sm">New Case</Link>
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
