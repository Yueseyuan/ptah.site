'use client';
import { useState } from 'react';
import { forgotPassword } from '@/lib/portal-api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#f5f7fa', padding: '24px 16px',
    }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>⚖</div>
          <h1 style={{ color: '#0a2540', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Cruel &amp; Associates
          </h1>
          <p style={{ color: '#64748b', marginTop: 6, fontSize: 14 }}>Reset your portal password</p>
        </div>

        <div style={{ background: '#fff', borderRadius: 12, padding: 32, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
          {sent ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>📬</div>
              <h2 style={{ color: '#0a2540', fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Check your email</h2>
              <p style={{ color: '#64748b', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
                If <strong>{email}</strong> is registered, we sent a reset link. It expires in 1 hour.
              </p>
              <p style={{ color: '#94a3b8', fontSize: 12, marginBottom: 20 }}>
                Didn&apos;t get it? Check your spam folder, or contact your case manager at{' '}
                <a href="mailto:yueseyuan.cruel@cruelandassociates.site" style={{ color: '#1d4ed8' }}>
                  yueseyuan.cruel@cruelandassociates.site
                </a>.
              </p>
              <a href="/portal/login" style={{
                display: 'inline-block', background: '#0a2540', color: '#fff',
                padding: '10px 24px', borderRadius: 8, fontSize: 14, fontWeight: 600,
                textDecoration: 'none',
              }}>
                Back to Login
              </a>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <p style={{ color: '#374151', fontSize: 14, lineHeight: 1.6, marginBottom: 20, marginTop: 0 }}>
                Enter the email address on your account and we&apos;ll send you a link to reset your password.
              </p>
              {error && (
                <div style={{
                  background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
                  borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 14,
                }}>
                  {error}
                </div>
              )}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoFocus
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' }}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                style={{ width: '100%', background: '#0a2540', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}
              >
                {loading ? 'Sending…' : 'Send Reset Link'}
              </button>
              <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#64748b' }}>
                <a href="/portal/login" style={{ color: '#1d4ed8', textDecoration: 'none' }}>Back to login</a>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
