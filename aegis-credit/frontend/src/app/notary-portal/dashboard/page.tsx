'use client';
import { useEffect, useState } from 'react';
import { notaryMe, notaryMyOrders, notaryUpdateOrder } from '@/lib/notary-api';

interface NotaryProfile {
  id: number; first_name: string; last_name: string; email: string;
  phone: string; license_number: string; license_state: string;
  license_expires: string; is_active: boolean;
}

interface Order {
  id: number; loan_number: string; borrower_name: string;
  borrower_phone: string; borrower_email: string;
  property_address: string; closing_date: string;
  signing_type: string; status: string; notes: string;
  fee: number | null; external_ref: string | null;
}

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  pending:    { bg: '#fef3c7', color: '#92400e' },
  assigned:   { bg: '#dbeafe', color: '#1e40af' },
  confirmed:  { bg: '#e0e7ff', color: '#3730a3' },
  completed:  { bg: '#d1fae5', color: '#065f46' },
  cancelled:  { bg: '#fee2e2', color: '#991b1b' },
};

const NEXT_STATUSES: Record<string, string[]> = {
  assigned:  ['confirmed', 'cancelled'],
  confirmed: ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
  pending:   ['assigned'],
};

export default function NotaryDashboardPage() {
  const [profile, setProfile] = useState<NotaryProfile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [updating, setUpdating] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([notaryMe(), notaryMyOrders()])
      .then(([me, mine]) => {
        setProfile(me);
        setOrders(mine as Order[]);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function updateStatus(orderId: number, status: string) {
    setUpdating(orderId);
    try {
      await notaryUpdateOrder(orderId, { status });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status } : o));
    } catch (err) {
      console.error(err);
    } finally {
      setUpdating(null);
    }
  }

  const filtered = filter === 'all' ? orders : orders.filter(o => o.status === filter);
  const counts = orders.reduce<Record<string, number>>((acc, o) => {
    acc[o.status] = (acc[o.status] || 0) + 1;
    return acc;
  }, {});

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 60, color: '#64748b', fontSize: 14 }}>Loading your orders…</div>
  );

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
          Welcome back
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: '#0f2d52', margin: '0 0 4px' }}>
          {profile ? `${profile.first_name} ${profile.last_name}` : 'Notary Dashboard'}
        </h1>
        {profile?.license_state && (
          <div style={{ fontSize: 13, color: '#64748b' }}>
            License #{profile.license_number} · {profile.license_state}
            {profile.license_expires && ` · Expires ${profile.license_expires}`}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 28 }}>
        {[
          { label: 'Total', count: orders.length, key: 'all' },
          { label: 'Assigned', count: counts.assigned || 0, key: 'assigned' },
          { label: 'Confirmed', count: counts.confirmed || 0, key: 'confirmed' },
          { label: 'Completed', count: counts.completed || 0, key: 'completed' },
        ].map(stat => (
          <button key={stat.key} onClick={() => setFilter(stat.key)} style={{
            background: filter === stat.key ? '#0f2d52' : '#fff',
            border: `1px solid ${filter === stat.key ? '#0f2d52' : '#e2e8f0'}`,
            borderRadius: 10, padding: '14px 16px', cursor: 'pointer', textAlign: 'left',
          }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: filter === stat.key ? '#fff' : '#0f2d52' }}>{stat.count}</div>
            <div style={{ fontSize: 11, color: filter === stat.key ? '#93c5fd' : '#64748b', fontWeight: 600 }}>{stat.label}</div>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '40px 24px', textAlign: 'center', color: '#94a3b8' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📋</div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
            {filter === 'all' ? 'No orders assigned yet' : `No ${filter} orders`}
          </div>
          <div style={{ fontSize: 13 }}>Orders will appear here once assigned by the coordinator.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filtered.map(order => {
            const sc = STATUS_COLORS[order.status] || { bg: '#f1f5f9', color: '#64748b' };
            const nextOpts = NEXT_STATUSES[order.status] || [];
            return (
              <div key={order.id} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15, color: '#0f2d52', marginBottom: 3 }}>
                      {order.borrower_name}
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      Loan #{order.loan_number} · {order.signing_type?.replace('_', ' ').toUpperCase()}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ background: sc.bg, color: sc.color, fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      {order.status}
                    </span>
                    {order.fee && <span style={{ fontSize: 13, fontWeight: 700, color: '#0f2d52' }}>${order.fee}</span>}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: nextOpts.length > 0 ? 16 : 0 }}>
                  {order.property_address && (
                    <InfoItem label="Property" value={order.property_address} />
                  )}
                  {order.closing_date && (
                    <InfoItem label="Closing Date" value={new Date(order.closing_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })} />
                  )}
                  {order.borrower_phone && (
                    <InfoItem label="Borrower Phone" value={order.borrower_phone} />
                  )}
                  {order.borrower_email && (
                    <InfoItem label="Borrower Email" value={order.borrower_email} />
                  )}
                </div>

                {order.notes && (
                  <div style={{ background: '#f8fafc', borderRadius: 6, padding: '8px 12px', fontSize: 12, color: '#475569', marginBottom: nextOpts.length > 0 ? 14 : 0 }}>
                    <span style={{ fontWeight: 600 }}>Notes: </span>{order.notes}
                  </div>
                )}

                {nextOpts.length > 0 && (
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {nextOpts.map(ns => (
                      <button key={ns} onClick={() => updateStatus(order.id, ns)} disabled={updating === order.id}
                        style={{
                          background: ns === 'cancelled' ? '#fef2f2' : '#0f2d52',
                          color: ns === 'cancelled' ? '#991b1b' : '#fff',
                          border: ns === 'cancelled' ? '1px solid #fecaca' : 'none',
                          borderRadius: 6, padding: '6px 14px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                        }}>
                        {updating === order.id ? '…' : `Mark ${ns.charAt(0).toUpperCase() + ns.slice(1)}`}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color: '#1e293b' }}>{value}</div>
    </div>
  );
}
