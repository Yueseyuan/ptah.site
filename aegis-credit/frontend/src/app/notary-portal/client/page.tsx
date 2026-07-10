'use client';
import { useState } from 'react';

interface AppointmentStatus {
  loan_number: string;
  borrower_name: string;
  property_address: string;
  closing_date: string;
  signing_type: string;
  status: string;
  notary_name: string;
  notary_phone: string;
  notes: string;
}

const STATUS_INFO: Record<string, { label: string; color: string; bg: string; desc: string }> = {
  pending:    { label: 'Pending', color: '#92400e', bg: '#fef3c7', desc: 'Your appointment is being scheduled.' },
  assigned:   { label: 'Notary Assigned', color: '#1e40af', bg: '#dbeafe', desc: 'A notary has been assigned to your closing.' },
  confirmed:  { label: 'Confirmed', color: '#3730a3', bg: '#e0e7ff', desc: 'Your appointment is confirmed. See details below.' },
  completed:  { label: 'Completed', color: '#065f46', bg: '#d1fae5', desc: 'Your signing is complete. Congratulations!' },
  cancelled:  { label: 'Cancelled', color: '#991b1b', bg: '#fee2e2', desc: 'This appointment has been cancelled. Please contact us.' },
};

export default function NotaryClientPage() {
  const [loanNumber, setLoanNumber] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AppointmentStatus | null>(null);

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/api/notary/orders/lookup?loan_number=${encodeURIComponent(loanNumber)}&email=${encodeURIComponent(email)}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'No appointment found with that information.');
      }
      const data = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError((err as Error).message || 'Lookup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const statusInfo = result ? (STATUS_INFO[result.status] || STATUS_INFO.pending) : null;

  return (
    <div style={{
      minHeight: '100vh', background: '#f0f4f8',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <a href="/notary-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🏠</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f2d52' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Track Your Signing</div>
          </a>
        </div>

        {!result ? (
          <div style={{ background: '#fff', borderRadius: 14, padding: '32px 28px', boxShadow: '0 2px 16px rgba(0,0,0,0.08)' }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: '#0f2d52', margin: '0 0 6px' }}>Look up your appointment</h2>
            <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 24px', lineHeight: 1.55 }}>
              Enter your loan number and the email address on file to view your signing status and notary details.
            </p>

            {error && (
              <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>
            )}

            <form onSubmit={handleLookup}>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Loan Number</label>
                <input
                  type="text" required value={loanNumber} onChange={e => setLoanNumber(e.target.value)}
                  placeholder="e.g. 1234567890"
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }}
                />
              </div>
              <div style={{ marginBottom: 22 }}>
                <label style={labelStyle}>Email Address on File</label>
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' as const }}
                />
              </div>
              <button type="submit" disabled={loading} style={btnStyle}>
                {loading ? 'Looking up…' : 'Find My Appointment →'}
              </button>
            </form>

            <div style={{ marginTop: 20, padding: '14px 16px', background: '#f8fafc', borderRadius: 8, fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>
              <strong style={{ color: '#374151' }}>Need help?</strong> Call or text us at your coordinator&apos;s number, or email <a href="mailto:notary@cruelandassociates.com" style={{ color: '#0f2d52' }}>notary@cruelandassociates.com</a>.
            </div>
          </div>
        ) : (
          <div>
            <div style={{ background: statusInfo!.bg, border: `1px solid ${statusInfo!.color}33`, borderRadius: 12, padding: '20px 22px', marginBottom: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: statusInfo!.color, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                {statusInfo!.label}
              </div>
              <div style={{ fontSize: 14, color: statusInfo!.color }}>{statusInfo!.desc}</div>
            </div>

            <div style={{ background: '#fff', borderRadius: 12, padding: '22px 24px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0f2d52', margin: '0 0 16px' }}>Appointment Details</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Row label="Borrower" value={result.borrower_name} />
                <Row label="Loan Number" value={result.loan_number} />
                <Row label="Property" value={result.property_address} />
                {result.closing_date && (
                  <Row label="Closing Date" value={new Date(result.closing_date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} />
                )}
                <Row label="Signing Type" value={result.signing_type?.replace('_', ' ')} />
              </div>
            </div>

            {(result.notary_name || result.notary_phone) && (
              <div style={{ background: '#fff', borderRadius: 12, padding: '22px 24px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', marginBottom: 16 }}>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#0f2d52', margin: '0 0 16px' }}>Your Notary</h3>
                {result.notary_name && <Row label="Name" value={result.notary_name} />}
                {result.notary_phone && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Phone</div>
                    <a href={`tel:${result.notary_phone}`} style={{ fontSize: 14, color: '#0f2d52', fontWeight: 600, textDecoration: 'none' }}>
                      {result.notary_phone}
                    </a>
                  </div>
                )}
              </div>
            )}

            {result.notes && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '14px 16px', marginBottom: 16, fontSize: 13, color: '#475569' }}>
                <strong style={{ color: '#374151' }}>Notes: </strong>{result.notes}
              </div>
            )}

            <button onClick={() => { setResult(null); setLoanNumber(''); setEmail(''); }} style={{ ...btnStyle, background: 'transparent', color: '#0f2d52', border: '1px solid #bfdbfe' }}>
              ← Look up another appointment
            </button>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <a href="/" style={{ color: '#94a3b8', fontSize: 12, textDecoration: 'none' }}>← Back to main site</a>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14, color: '#1e293b' }}>{value}</div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 };
const inputStyle: React.CSSProperties = { padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: 'system-ui, sans-serif' };
const btnStyle: React.CSSProperties = { width: '100%', background: '#0f2d52', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' };
