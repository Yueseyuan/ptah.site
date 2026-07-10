'use client';
import { useEffect, useState } from 'react';

interface ServiceCase {
  id: number;
  case_number: string;
  division_slug: string;
  title: string;
  status: string;
  created_at: string;
  intake_data?: Record<string, unknown>;
}

const STATUS_INFO: Record<string, { label: string; color: string; bg: string }> = {
  pending:     { label: 'Under Review', color: '#92400e', bg: '#fef3c7' },
  in_progress: { label: 'In Progress',  color: '#1e40af', bg: '#dbeafe' },
  completed:   { label: 'Completed',    color: '#065f46', bg: '#d1fae5' },
  on_hold:     { label: 'On Hold',      color: '#6b21a8', bg: '#f3e8ff' },
  closed:      { label: 'Closed',       color: '#374151', bg: '#f3f4f6' },
};

export default function CriminalPortalDashboardPage() {
  const [cases, setCases] = useState<ServiceCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('criminal_token');
    fetch('/api/portal/service-cases', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : r.json().then((e: { detail?: string }) => Promise.reject(new Error(e.detail || 'Failed'))))
      .then((data: ServiceCase[]) => setCases(data.filter(c => c.division_slug === 'criminal')))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 60, color: '#64748b', fontSize: 14 }}>Loading your cases…</div>
  );

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Record Relief</div>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1a1a2e', margin: '0 0 6px' }}>My Cases</h1>
        <p style={{ fontSize: 14, color: '#64748b', margin: 0 }}>Track your expungement and record relief cases below.</p>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 20, fontSize: 14 }}>{error}</div>
      )}

      {cases.length === 0 ? (
        <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '48px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 36, marginBottom: 16 }}>⚖️</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a2e', marginBottom: 8 }}>No cases yet</div>
          <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24, lineHeight: 1.6 }}>
            Submit your criminal record intake to get started. We will review your eligibility and reach out within 1 business day.
          </p>
          <a href="/portal/criminal" style={{
            background: '#7c3aed', color: '#fff', textDecoration: 'none',
            padding: '11px 24px', borderRadius: 8, fontSize: 14, fontWeight: 600, display: 'inline-block',
          }}>
            Start Criminal Record Intake →
          </a>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {cases.map(c => {
            const si = STATUS_INFO[c.status] || STATUS_INFO.pending;
            const intake = c.intake_data || {};
            return (
              <div key={c.id} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 22px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 16, color: '#1a1a2e', letterSpacing: -0.3, marginBottom: 2 }}>
                      {c.case_number}
                    </div>
                    <div style={{ fontSize: 13, color: '#475569' }}>{c.title}</div>
                  </div>
                  <span style={{ background: si.bg, color: si.color, fontSize: 11, fontWeight: 700, padding: '4px 12px', borderRadius: 20, textTransform: 'uppercase', letterSpacing: 0.5, whiteSpace: 'nowrap' }}>
                    {si.label}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 14 }}>
                  {intake.state && <InfoItem label="State" value={String(intake.state)} />}
                  {intake.record_type && <InfoItem label="Record Type" value={String(intake.record_type).replace(/_/g, ' ')} />}
                  {intake.county && <InfoItem label="County" value={String(intake.county)} />}
                  {intake.charge_year && <InfoItem label="Year of Charge" value={String(intake.charge_year)} />}
                  {intake.outcome && <InfoItem label="Outcome" value={String(intake.outcome).replace(/_/g, ' ')} />}
                  <InfoItem label="Submitted" value={new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} />
                </div>

                <div style={{ background: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#6d28d9', lineHeight: 1.5 }}>
                  Our team will contact you to discuss eligibility and next steps. Questions? Call or email your case coordinator.
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <a href="/portal/criminal" style={{ color: '#7c3aed', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
          + Submit Another Record for Review
        </a>
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color: '#1e293b', textTransform: 'capitalize' }}>{value}</div>
    </div>
  );
}
