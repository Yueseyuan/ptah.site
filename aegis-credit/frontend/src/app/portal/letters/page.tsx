'use client';
import { useEffect, useState } from 'react';
import { portalApi } from '@/lib/portal-api';

interface DisputeLetter {
  id: string;
  type: 'dispute';
  round_id: number;
  label: string;
  recipient: string;
  round_number: number;
  status: string;
  sent_date: string | null;
  download_url: string;
}

interface StaticLetter {
  id: string;
  type: 'affidavit' | 'authorization';
  label: string;
  recipient: string;
  download_url: string;
}

interface LettersData {
  dispute_letters: DisputeLetter[];
  static_letters: StaticLetter[];
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  draft:     { bg: '#f1f5f9', text: '#475569' },
  sent:      { bg: '#eff6ff', text: '#1d4ed8' },
  responded: { bg: '#fef9c3', text: '#92400e' },
  escalated: { bg: '#fef2f2', text: '#991b1b' },
  resolved:  { bg: '#f0fdf4', text: '#166534' },
  closed:    { bg: '#f0fdf4', text: '#166534' },
};

export default function PortalLettersPage() {
  const [data, setData] = useState<LettersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    portalApi.get('/api/portal/letters')
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load letters.'))
      .finally(() => setLoading(false));
  }, []);

  async function download(url: string, filename: string, id: string) {
    setDownloading(id);
    try {
      const res = await portalApi.get(url, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      alert('Download failed. Please try again or contact your case manager.');
    } finally {
      setDownloading(null);
    }
  }

  const totalLetters = data
    ? data.dispute_letters.length + data.static_letters.length
    : 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>My Letters</h2>
        <p style={{ color: '#64748b', marginTop: 4, fontSize: 14 }}>
          Download dispute letters, affidavits, and authorization documents prepared for your case.
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
      ) : totalLetters === 0 ? (
        <div style={{
          background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
          padding: '48px 24px', textAlign: 'center',
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📬</div>
          <h3 style={{ color: '#0a2540', fontSize: 16, fontWeight: 700, margin: '0 0 8px' }}>
            No Letters Ready Yet
          </h3>
          <p style={{ color: '#64748b', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
            Letters will appear here once your case manager begins preparing disputes.
            Make sure your profile is complete and documents are uploaded.
          </p>
        </div>
      ) : (
        <div>
          {/* Static Letters — always available once case exists */}
          {data && data.static_letters.length > 0 && (
            <Section label="Case Documents">
              {data.static_letters.map(letter => (
                <LetterRow
                  key={letter.id}
                  icon={letter.type === 'affidavit' ? '📜' : '✍️'}
                  label={letter.label}
                  sub={letter.recipient}
                  badge={null}
                  downloading={downloading === letter.id}
                  onDownload={() => download(
                    letter.download_url,
                    `${letter.label.replace(/\s+/g, '_')}_${today()}.txt`,
                    letter.id,
                  )}
                />
              ))}
            </Section>
          )}

          {/* Dispute Letters */}
          {data && data.dispute_letters.length > 0 && (
            <Section label={`Dispute Letters (${data.dispute_letters.length})`}>
              {data.dispute_letters.map(letter => {
                const bc = STATUS_COLORS[letter.status] || STATUS_COLORS.draft;
                return (
                  <LetterRow
                    key={letter.id}
                    icon="⚖"
                    label={`Round ${letter.round_number} — ${letter.label}`}
                    sub={letter.recipient || ''}
                    badge={{ label: capitalize(letter.status), ...bc }}
                    sentDate={letter.sent_date}
                    downloading={downloading === letter.id}
                    onDownload={() => download(
                      letter.download_url,
                      `Letter_Round${letter.round_number}_${(letter.recipient || 'letter').replace(/\s+/g, '_')}_${today()}.txt`,
                      letter.id,
                    )}
                  />
                );
              })}
            </Section>
          )}
        </div>
      )}

      <div style={{
        background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 10,
        padding: '12px 16px', marginTop: 16, fontSize: 12, color: '#0c4a6e', lineHeight: 1.6,
      }}>
        <strong>Instructions:</strong> Letters download as .txt files. Print on standard paper,
        sign where indicated, and mail via <strong>Certified Mail with Return Receipt Requested</strong>.
        Keep your green card (PS Form 3811) as proof of delivery — it is critical evidence.
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12,
      padding: 24, marginBottom: 16,
    }}>
      <div style={{
        fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase',
        letterSpacing: 0.8, marginBottom: 16, borderBottom: '1px solid #f1f5f9', paddingBottom: 8,
      }}>
        {label}
      </div>
      {children}
    </div>
  );
}

function LetterRow({
  icon, label, sub, badge, sentDate, downloading, onDownload,
}: {
  icon: string;
  label: string;
  sub: string;
  badge: { label: string; bg: string; text: string } | null;
  sentDate?: string | null;
  downloading: boolean;
  onDownload: () => void;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14,
      padding: '12px 0', borderBottom: '1px solid #f8fafc',
    }}>
      <div style={{
        width: 42, height: 42, background: '#eff6ff', borderRadius: 9,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 20, flexShrink: 0,
      }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 2 }}>
          {label}
        </div>
        <div style={{ fontSize: 12, color: '#64748b' }}>
          {sub}
          {sentDate && (
            <span style={{ marginLeft: 10, color: '#94a3b8' }}>
              Sent {new Date(sentDate).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {badge && (
          <span style={{
            background: badge.bg, color: badge.text,
            fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
          }}>
            {badge.label}
          </span>
        )}
        <button
          onClick={onDownload}
          disabled={downloading}
          style={{
            background: downloading ? '#e2e8f0' : '#0a2540',
            color: downloading ? '#94a3b8' : '#fff',
            border: 'none', borderRadius: 7, padding: '8px 16px',
            fontSize: 13, fontWeight: 600, cursor: downloading ? 'default' : 'pointer',
          }}
        >
          {downloading ? 'Downloading…' : '↓ Download'}
        </button>
      </div>
    </div>
  );
}

function today() {
  return new Date().toISOString().slice(0, 10).replace(/-/g, '');
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
