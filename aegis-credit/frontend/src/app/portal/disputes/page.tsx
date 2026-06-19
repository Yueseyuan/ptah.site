'use client';
import { useEffect, useState } from 'react';
import { portalDisputes } from '@/lib/portal-api';

interface DisputeItem {
  creditor_name: string;
  status: string;
  resolution: string | null;
}

interface DisputeRound {
  round_number: number;
  recipient_type: string;
  bureau: string | null;
  recipient_name: string | null;
  status: string;
  sent_date: string | null;
  response_due_date: string | null;
  items: DisputeItem[];
}

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  draft:       { bg: '#f1f5f9', text: '#475569', label: 'Draft' },
  sent:        { bg: '#eff6ff', text: '#1d4ed8', label: 'Sent' },
  responded:   { bg: '#fef9c3', text: '#92400e', label: 'Response Received' },
  escalated:   { bg: '#fef2f2', text: '#991b1b', label: 'Escalated' },
  resolved:    { bg: '#f0fdf4', text: '#166534', label: 'Resolved' },
  closed:      { bg: '#f0fdf4', text: '#166534', label: 'Closed' },
};

const ITEM_STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  disputed:  { bg: '#eff6ff', text: '#1d4ed8' },
  pending:   { bg: '#fef9c3', text: '#92400e' },
  deleted:   { bg: '#f0fdf4', text: '#166534' },
  corrected: { bg: '#f0fdf4', text: '#166534' },
  verified:  { bg: '#fef2f2', text: '#991b1b' },
  closed:    { bg: '#f1f5f9', text: '#475569' },
};

export default function PortalDisputesPage() {
  const [rounds, setRounds] = useState<DisputeRound[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    portalDisputes()
      .then(setRounds)
      .catch(() => setError('Failed to load dispute status.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>Dispute Status</h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Track the progress of disputes filed on your behalf. This is a read-only view.
        </p>
      </div>

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
      ) : rounds.length === 0 ? (
        <div style={{
          background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
          padding: '48px 24px', textAlign: 'center',
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📬</div>
          <h3 style={{ color: '#0a2540', fontSize: 16, fontWeight: 700, margin: '0 0 8px' }}>
            No Disputes Filed Yet
          </h3>
          <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>
            Once your case manager begins filing disputes, you will see real-time updates here.
            Make sure you have uploaded your credit reports and completed your profile.
          </p>
        </div>
      ) : (
        <div>
          {rounds.map((round, idx) => {
            const badge = STATUS_BADGE[round.status] || STATUS_BADGE.draft;
            return (
              <div key={idx} style={{
                background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
                padding: 24, marginBottom: 16,
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>
                      Round {round.round_number}
                    </div>
                    <div style={{ fontSize: 17, fontWeight: 700, color: '#0a2540' }}>
                      {round.bureau || round.recipient_name || recipientLabel(round.recipient_type)}
                    </div>
                    <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
                      {formatRecipientType(round.recipient_type)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{
                      background: badge.bg, color: badge.text, fontSize: 12, fontWeight: 700,
                      padding: '4px 12px', borderRadius: 20,
                    }}>
                      {badge.label}
                    </span>
                    {round.sent_date && (
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
                        Sent: {new Date(round.sent_date).toLocaleDateString()}
                      </div>
                    )}
                    {round.response_due_date && (
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                        Response due: {new Date(round.response_due_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>

                {round.items.length > 0 && (
                  <div>
                    <div style={{
                      fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
                      letterSpacing: 0.6, marginBottom: 8,
                    }}>
                      Disputed Items ({round.items.length})
                    </div>
                    {round.items.map((item, i) => {
                      const ib = ITEM_STATUS_BADGE[item.status] || ITEM_STATUS_BADGE.disputed;
                      return (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'center', gap: 12,
                          padding: '9px 0', borderBottom: i < round.items.length - 1 ? '1px solid #f1f5f9' : 'none',
                        }}>
                          <div style={{ flex: 1 }}>
                            <span style={{ fontSize: 14, color: '#1e293b', fontWeight: 500 }}>
                              {item.creditor_name}
                            </span>
                            {item.resolution && (
                              <span style={{ fontSize: 12, color: '#64748b', marginLeft: 8 }}>
                                — {item.resolution}
                              </span>
                            )}
                          </div>
                          <span style={{
                            background: ib.bg, color: ib.text, fontSize: 11, fontWeight: 700,
                            padding: '2px 10px', borderRadius: 20, flexShrink: 0,
                          }}>
                            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div style={{
        background: '#fef9c3', border: '1px solid #fde68a', borderRadius: 10,
        padding: '12px 16px', marginTop: 16, fontSize: 12, color: '#713f12', lineHeight: 1.6,
      }}>
        <strong>Note:</strong> Credit bureaus have 30 days to respond to disputes under
        15 U.S.C. §1681i. Debt collectors must respond within 30 days under 15 U.S.C. §1692g.
        If you have questions about a specific item, contact your case manager.
      </div>
    </div>
  );
}

function recipientLabel(type: string): string {
  const labels: Record<string, string> = {
    bureau: 'Credit Bureau',
    creditor: 'Creditor / Furnisher',
    debt_collector: 'Debt Collector',
    cfpb: 'CFPB Complaint',
    failure_to_investigate: 'Failure to Investigate',
  };
  return labels[type] || type;
}

function formatRecipientType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
