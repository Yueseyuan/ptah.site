'use client';
import { useState } from 'react';

interface CroaDisclosureProps {
  onAccept: () => void;
  onDecline?: () => void;
  /** If true, renders inline (no modal overlay) */
  inline?: boolean;
}

export default function CroaDisclosure({ onAccept, onDecline, inline = false }: CroaDisclosureProps) {
  const [checked, setChecked] = useState(false);

  const content = (
    <div style={{
      background: '#fff',
      borderRadius: inline ? 10 : 12,
      padding: inline ? '20px 22px' : 32,
      maxWidth: inline ? '100%' : 620,
      width: '100%',
      boxShadow: inline ? '0 1px 4px rgba(0,0,0,0.08)' : '0 8px 40px rgba(0,0,0,0.18)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <span style={{ fontSize: 22 }}>⚖</span>
        <h2 style={{ margin: 0, color: '#0a2540', fontSize: 18, fontWeight: 700 }}>
          Required Disclosure — Consumer Credit File Rights
        </h2>
      </div>

      <div style={{
        background: '#fffbeb', border: '1px solid #fde68a',
        borderRadius: 8, padding: '12px 14px', marginBottom: 16,
        fontSize: 12, color: '#78350f', fontWeight: 600,
      }}>
        IMPORTANT NOTICE — Please read this disclosure carefully before proceeding.
        This notice is required by the Credit Repair Organizations Act (15 U.S.C. §1679c).
      </div>

      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0',
        borderRadius: 8, padding: '16px 18px', marginBottom: 18,
        fontSize: 13, color: '#1e293b', lineHeight: 1.75,
        maxHeight: 320, overflowY: 'auto',
      }}>
        <p style={{ margin: '0 0 10px', fontWeight: 700, textDecoration: 'underline' }}>
          Consumer Credit File Rights Under State and Federal Law
        </p>

        <p style={{ margin: '0 0 10px' }}>
          You have a right to dispute inaccurate information in your credit report by contacting the
          credit bureau directly. However, neither you nor any "credit repair" company or credit
          repair organization has the right to have <em>accurate, current, and verifiable</em> information
          removed from your credit report. The credit bureau must remove accurate negative information
          from your report only if it is over 7 years old. Bankruptcy information can be reported for
          10 years.
        </p>

        <p style={{ margin: '0 0 10px' }}>
          You have a right to obtain a copy of your credit report from a credit bureau. You may be
          charged a reasonable fee. There is no fee, however, if you have been turned down for credit,
          employment, insurance, or a rental dwelling because of information in your credit report within
          the preceding 60 days. The credit bureau must provide someone to help you interpret the
          information in your credit file. You are entitled to receive a free copy of your credit report
          annually from each of the three major credit reporting agencies.
        </p>

        <p style={{ margin: '0 0 10px' }}>
          You have a right to sue a credit repair organization that violates the Credit Repair
          Organizations Act. This law prohibits deceptive practices by credit repair organizations.
        </p>

        <p style={{ margin: '0 0 10px' }}>
          You have the right to cancel your contract with any credit repair organization for any reason
          within 3 business days from the date you signed it. Credit repair organizations are prohibited
          by law from taking money from you before they have completed the promised services.
        </p>

        <p style={{ margin: '0 0 10px' }}>
          Non-Attorney Notice: Cruel &amp; Associates is a <strong>credit services organization</strong>,
          not a law firm. We do not provide legal advice and do not represent you as your attorney.
          Our services consist of document preparation, consumer education, and administrative dispute
          assistance. No outcome is guaranteed. If you require legal representation, you should consult
          a licensed attorney.
        </p>

        <p style={{ margin: 0, color: '#475569' }}>
          15 U.S.C. §§1679–1679j • FTC Rule 16 CFR Part 455 • South Carolina Consumer Protection Code
        </p>
      </div>

      <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 20, cursor: 'pointer' }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={e => setChecked(e.target.checked)}
          style={{ marginTop: 2, width: 16, height: 16, flexShrink: 0, cursor: 'pointer' }}
        />
        <span style={{ fontSize: 13, color: '#374151', lineHeight: 1.5 }}>
          I have read and understand the Consumer Credit File Rights disclosure above. I acknowledge
          that Cruel &amp; Associates is not a law firm and does not provide legal advice. I understand
          my right to cancel within 3 business days.
        </span>
      </label>

      <div style={{ display: 'flex', gap: 10 }}>
        <button
          onClick={onAccept}
          disabled={!checked}
          style={{
            flex: 1, background: checked ? '#0a2540' : '#cbd5e1',
            color: '#fff', border: 'none', borderRadius: 8,
            padding: '12px 0', fontSize: 14, fontWeight: 600,
            cursor: checked ? 'pointer' : 'not-allowed', transition: 'background 0.15s',
          }}
        >
          I Acknowledge &amp; Continue
        </button>
        {onDecline && (
          <button
            onClick={onDecline}
            style={{
              padding: '12px 18px', background: 'transparent',
              border: '1px solid #d1d5db', borderRadius: 8,
              color: '#6b7280', fontSize: 14, cursor: 'pointer',
            }}
          >
            Decline
          </button>
        )}
      </div>
    </div>
  );

  if (inline) return content;

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 9999, padding: '24px 16px',
    }}>
      {content}
    </div>
  );
}
