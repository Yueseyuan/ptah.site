'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import { getClient, listCases } from '@/lib/api';

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [client, setClient] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getClient(Number(id)), listCases({ client_id: id })])
      .then(([c, cs]) => { setClient(c); setCases(cs); })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="main-layout"><Sidebar /><main className="main-content"><div className="spinner" /></main></div>
  );
  if (!client) return (
    <div className="main-layout"><Sidebar /><main className="main-content"><p>Client not found.</p></main></div>
  );

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>{client.first_name} {client.last_name}</h1>
            <p>Client #{client.id} · Added {new Date(client.created_at).toLocaleDateString()}</p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Link href={`/cases/new?client_id=${client.id}`} className="btn btn-primary">+ New Case</Link>
            <button onClick={() => router.back()} className="btn btn-outline">Back</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 14, fontSize: 15 }}>Contact</h3>
            <div style={{ fontSize: 14, lineHeight: 2.2 }}>
              {client.email && <div><b>Email:</b> {client.email}</div>}
              {client.phone && <div><b>Phone:</b> {client.phone}</div>}
              {client.dob && <div><b>DOB:</b> {client.dob}</div>}
              {client.ssn_last4 && <div><b>SSN:</b> ***-**-{client.ssn_last4}</div>}
            </div>
          </div>
          <div className="card">
            <h3 style={{ color: 'var(--navy)', marginBottom: 14, fontSize: 15 }}>Address</h3>
            <div style={{ fontSize: 14, lineHeight: 2.2 }}>
              {client.address && <div>{client.address}</div>}
              <div>{[client.city, client.state, client.zip_code].filter(Boolean).join(', ') || '—'}</div>
            </div>
            {client.notes && (
              <>
                <h3 style={{ color: 'var(--navy)', marginTop: 16, marginBottom: 8, fontSize: 15 }}>Notes</h3>
                <p style={{ fontSize: 13, color: 'var(--muted)' }}>{client.notes}</p>
              </>
            )}
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: 'var(--navy)', fontSize: 15 }}>Cases ({cases.length})</h3>
            <Link href={`/cases/new?client_id=${client.id}`} className="btn btn-primary btn-sm">+ Open Case</Link>
          </div>
          {cases.length === 0 ? (
            <p style={{ color: 'var(--muted)', textAlign: 'center', padding: 24 }}>No cases yet.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Title</th><th>Division</th><th>Status</th><th>Date</th><th></th></tr>
              </thead>
              <tbody>
                {cases.map((c: any) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>{c.title}</td>
                    <td>{c.division}</td>
                    <td><span style={{
                      background: '#3b82f6', color: 'white', borderRadius: 4,
                      padding: '2px 8px', fontSize: 11,
                    }}>{c.status}</span></td>
                    <td style={{ color: 'var(--muted)', fontSize: 13 }}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td><Link href={`/cases/${c.id}`} className="btn btn-outline btn-sm">View</Link></td>
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
