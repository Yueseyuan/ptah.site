'use client';
import { useEffect, useState } from 'react';
import { portalMe } from '@/lib/portal-api';

interface PortalData {
  user: { username: string; email: string };
  client: {
    id: number; first_name: string; last_name: string; email: string;
    phone: string; address: string; city: string; state: string;
    zip_code: string; dob: string; ssn_last4: string;
  };
  case: {
    id: number; case_number: string; status: string;
    portal_status: string; portal_status_label: string;
    goal: string; created_at: string;
  } | null;
  documents_uploaded: number;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  pending:      { bg: '#fef9c3', text: '#713f12', border: '#fde68a' },
  docs_needed:  { bg: '#fff7ed', text: '#9a3412', border: '#fdba74' },
  under_review: { bg: '#eff6ff', text: '#1e3a8a', border: '#93c5fd' },
  active:       { bg: '#f0fdf4', text: '#14532d', border: '#86efac' },
  completed:    { bg: '#f0fdf4', text: '#14532d', border: '#86efac' },
};

const DOC_CHECKLIST = [
  { key: 'credit_reports', label: 'Credit Reports (Experian, Equifax, TransUnion)', required: true },
  { key: 'drivers_license', label: "Driver's License or Government ID", required: true },
  { key: 'proof_of_address', label: 'Proof of Address (utility bill, bank statement)', required: true },
  { key: 'supporting_doc', label: 'Supporting Documents (collection letters, statements)', required: false },
];

export default function PortalDashboard() {
  const [data, setData] = useState<PortalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    portalMe()
      .then(setData)
      .catch(() => setError('Failed to load your account. Please try again.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const { client, case: caseData, documents_uploaded } = data;
  const portalStatus = caseData?.portal_status || 'pending';
  const statusColors = STATUS_COLORS[portalStatus] || STATUS_COLORS.pending;

  const profileComplete = !!(client.phone && client.address && client.dob && client.ssn_last4);
  const docsReady = documents_uploaded >= 3;

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>
          Welcome, {client.first_name}
        </h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Here&apos;s the current status of your case.
        </p>
      </div>

      {/* Case Status Banner */}
      {caseData && (
        <div style={{
          background: statusColors.bg, border: `1px solid ${statusColors.border}`,
          borderRadius: 12, padding: '20px 24px', marginBottom: 24,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: statusColors.text, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>
              Case Status
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: statusColors.text }}>
              {caseData.portal_status_label}
            </div>
            <div style={{ fontSize: 13, color: statusColors.text, opacity: 0.8, marginTop: 4 }}>
              Case #{caseData.case_number}
            </div>
          </div>
          <div style={{ textAlign: 'right', fontSize: 12, color: statusColors.text, opacity: 0.8 }}>
            <div>Opened</div>
            <div style={{ fontWeight: 600 }}>
              {caseData.created_at ? new Date(caseData.created_at).toLocaleDateString() : '—'}
            </div>
          </div>
        </div>
      )}

      {/* Action Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <ActionCard
          icon="👤"
          title="Profile"
          status={profileComplete ? 'complete' : 'action'}
          statusLabel={profileComplete ? 'Complete' : 'Action Required'}
          description={profileComplete
            ? 'Your personal information is on file.'
            : 'Please complete your personal information so we can prepare your case.'
          }
          linkHref="/portal/profile"
          linkLabel={profileComplete ? 'Review Profile' : 'Complete Profile'}
        />
        <ActionCard
          icon="📄"
          title="Documents"
          status={docsReady ? 'complete' : 'action'}
          statusLabel={docsReady ? `${documents_uploaded} Uploaded` : `${documents_uploaded} of 3+ Needed`}
          description={docsReady
            ? 'Documents received. Your case manager will review them.'
            : 'Upload your credit reports and ID to get started.'
          }
          linkHref="/portal/documents"
          linkLabel="Manage Documents"
        />
        <ActionCard
          icon="⚖"
          title="Dispute Status"
          status="info"
          statusLabel="View Progress"
          description="Track the status of active disputes with the credit bureaus and creditors."
          linkHref="/portal/disputes"
          linkLabel="View Disputes"
        />
        <ActionCard
          icon="📩"
          title="My Letters"
          status="info"
          statusLabel="Download"
          description="Download dispute letters, affidavits, and your authorization document prepared for your case."
          linkHref="/portal/letters"
          linkLabel="View Letters"
        />
        <ActionCard
          icon="📬"
          title="Need Help?"
          status="info"
          statusLabel="Contact Us"
          description="Questions about your case? Reach out to your assigned case manager directly."
          linkHref="mailto:info@cruelandassociates.site"
          linkLabel="Send Email"
        />
      </div>

      {/* Document Checklist */}
      <div style={{
        background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0a2540', margin: '0 0 16px' }}>
          Document Checklist
        </h3>
        {DOC_CHECKLIST.map(item => (
          <div key={item.key} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 0', borderBottom: '1px solid #f1f5f9',
          }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%',
              background: documents_uploaded > 0 ? '#dcfce7' : '#f1f5f9',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, color: documents_uploaded > 0 ? '#16a34a' : '#94a3b8',
              flexShrink: 0,
            }}>
              {documents_uploaded > 0 ? '✓' : '○'}
            </div>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 14, color: '#374151' }}>{item.label}</span>
              {item.required && (
                <span style={{ fontSize: 11, color: '#ef4444', marginLeft: 6 }}>Required</span>
              )}
            </div>
          </div>
        ))}
        <div style={{ marginTop: 14 }}>
          <a href="/portal/documents" style={{
            display: 'inline-block', background: '#0a2540', color: '#fff',
            padding: '9px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            textDecoration: 'none',
          }}>
            Upload Documents
          </a>
        </div>
      </div>
    </div>
  );
}

function ActionCard({
  icon, title, status, statusLabel, description, linkHref, linkLabel,
}: {
  icon: string; title: string; status: 'complete' | 'action' | 'info';
  statusLabel: string; description: string; linkHref: string; linkLabel: string;
}) {
  const badgeColors = {
    complete: { bg: '#dcfce7', text: '#16a34a' },
    action: { bg: '#fef9c3', text: '#92400e' },
    info: { bg: '#eff6ff', text: '#1e40af' },
  };
  const bc = badgeColors[status];

  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
      padding: '20px', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 20 }}>{icon}</span>
          <span style={{ fontWeight: 700, color: '#0a2540', fontSize: 15 }}>{title}</span>
        </div>
        <span style={{
          background: bc.bg, color: bc.text, fontSize: 11, fontWeight: 700,
          padding: '3px 10px', borderRadius: 20,
        }}>
          {statusLabel}
        </span>
      </div>
      <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 16px', lineHeight: 1.5, flex: 1 }}>
        {description}
      </p>
      <a href={linkHref} style={{
        color: '#1d4ed8', fontSize: 13, fontWeight: 600, textDecoration: 'none',
      }}>
        {linkLabel} →
      </a>
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>
      Loading your account…
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div style={{
      background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
      borderRadius: 8, padding: '16px 20px', fontSize: 14,
    }}>
      {message}
    </div>
  );
}
