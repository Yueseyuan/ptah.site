'use client';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { portalApi } from '@/lib/portal-api';

interface BillingStatus {
  subscription_status: string | null;
  subscription_period_end: string | null;
  stripe_customer_id: string | null;
  publishable_key: string;
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; border: string; icon: string }> = {
  active:   { label: 'Active', bg: '#f0fdf4', text: '#166534', border: '#86efac', icon: '✓' },
  trialing: { label: 'Trial', bg: '#eff6ff', text: '#1d4ed8', border: '#93c5fd', icon: '◎' },
  past_due: { label: 'Payment Due', bg: '#fef9c3', text: '#92400e', border: '#fde68a', icon: '!' },
  canceled: { label: 'Canceled', bg: '#fef2f2', text: '#991b1b', border: '#fecaca', icon: '✕' },
  unpaid:   { label: 'Unpaid', bg: '#fef2f2', text: '#991b1b', border: '#fecaca', icon: '!' },
};

export default function PortalBillingPage() {
  const searchParams = useSearchParams();
  const paymentSuccess = searchParams.get('payment') === 'success';

  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    portalApi.get('/api/portal/billing/status')
      .then(r => setStatus(r.data))
      .catch(() => setError('Failed to load billing status.'))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubscribe() {
    setActionLoading(true);
    setError('');
    try {
      const res = await portalApi.post('/api/portal/billing/create-checkout');
      window.location.href = res.data.checkout_url;
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Could not start checkout. Please try again.');
      setActionLoading(false);
    }
  }

  async function handleManage() {
    setActionLoading(true);
    setError('');
    try {
      const res = await portalApi.post('/api/portal/billing/customer-portal');
      window.location.href = res.data.portal_url;
    } catch {
      setError('Could not open billing portal. Please try again.');
      setActionLoading(false);
    }
  }

  const subStatus = status?.subscription_status;
  const isActive = subStatus === 'active' || subStatus === 'trialing';
  const cfg = subStatus ? STATUS_CONFIG[subStatus] : null;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>Billing</h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Manage your monthly consulting retainer subscription.
        </p>
      </div>

      {paymentSuccess && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #86efac', color: '#166534',
          borderRadius: 10, padding: '14px 18px', marginBottom: 20, fontSize: 14,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 18 }}>✓</span>
          <span>Payment successful — your subscription is now active. Welcome to Cruel &amp; Associates.</span>
        </div>
      )}

      {error && (
        <div style={{
          background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
          borderRadius: 8, padding: '12px 16px', marginBottom: 16, fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>Loading…</div>
      ) : (
        <div>
          {/* Subscription Card */}
          <div style={{
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 28,
            marginBottom: 20,
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>
                  Monthly Consulting Retainer
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#0a2540' }}>
                  $149<span style={{ fontSize: 16, fontWeight: 400, color: '#64748b' }}>/month</span>
                </div>
              </div>
              {cfg ? (
                <div style={{
                  background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.text,
                  borderRadius: 20, padding: '6px 16px', fontSize: 13, fontWeight: 700,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <span>{cfg.icon}</span> {cfg.label}
                </div>
              ) : (
                <div style={{
                  background: '#f1f5f9', color: '#64748b',
                  borderRadius: 20, padding: '6px 16px', fontSize: 13, fontWeight: 700,
                }}>
                  Not Subscribed
                </div>
              )}
            </div>

            {/* What's included */}
            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 20, marginBottom: 24 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 12 }}>
                Included Each Month
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 20px' }}>
                {[
                  'Credit bureau dispute letters',
                  'Affidavit of Truth preparation',
                  'Bureau response analysis',
                  'Debt collector FDCPA letters',
                  'CFPB complaint preparation',
                  'Failure to investigate escalation',
                  'Method of verification requests',
                  'Ongoing FCRA/FDCPA advisory',
                ].map(item => (
                  <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#374151' }}>
                    <span style={{ color: '#16a34a', fontWeight: 700, flexShrink: 0 }}>✓</span>
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* Renewal info */}
            {isActive && status?.subscription_period_end && (
              <div style={{
                background: '#f8fafc', borderRadius: 8, padding: '12px 16px',
                marginBottom: 20, fontSize: 13, color: '#475569',
              }}>
                Next billing date:{' '}
                <strong>{new Date(status.subscription_period_end).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</strong>
              </div>
            )}

            {/* CTA */}
            {!subStatus || subStatus === 'canceled' ? (
              <button onClick={handleSubscribe} disabled={actionLoading} style={primaryBtn}>
                {actionLoading ? 'Redirecting to checkout…' : 'Subscribe — $149/month'}
              </button>
            ) : subStatus === 'past_due' || subStatus === 'unpaid' ? (
              <div>
                <div style={{ color: '#92400e', fontSize: 13, marginBottom: 12 }}>
                  Your last payment failed. Update your payment method to keep your case active.
                </div>
                <button onClick={handleManage} disabled={actionLoading} style={primaryBtn}>
                  {actionLoading ? 'Opening…' : 'Update Payment Method'}
                </button>
              </div>
            ) : isActive ? (
              <button onClick={handleManage} disabled={actionLoading} style={secondaryBtn}>
                {actionLoading ? 'Opening…' : 'Manage Subscription'}
              </button>
            ) : null}
          </div>

          {/* Cancel notice */}
          {isActive && (
            <div style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
              You can cancel anytime with no penalty. Click &ldquo;Manage Subscription&rdquo; above to cancel.
              Per the Credit Repair Organizations Act (15 U.S.C. §1679b), you may cancel without obligation.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const primaryBtn: React.CSSProperties = {
  background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8,
  padding: '13px 28px', fontSize: 15, fontWeight: 600, cursor: 'pointer', width: '100%',
};

const secondaryBtn: React.CSSProperties = {
  background: 'transparent', color: '#0a2540', border: '2px solid #0a2540',
  borderRadius: 8, padding: '11px 28px', fontSize: 14, fontWeight: 600,
  cursor: 'pointer',
};
