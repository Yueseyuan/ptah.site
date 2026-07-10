'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { notaryLogin, setNotaryAuth } from '@/lib/notary-api';

export default function NotaryLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await notaryLogin(email, password);
      setNotaryAuth(data.access_token, 'notary');
      router.replace('/notary-portal/dashboard');
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#f0f4f8',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <a href="/notary-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🖊️</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f2d52' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Notary Portal</div>
          </a>
        </div>

        <div style={{ background: '#fff', borderRadius: 14, padding: '32px 28px', boxShadow: '0 2px 16px rgba(0,0,0,0.08)' }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f2d52', margin: '0 0 6px' }}>Sign in to your account</h2>
          <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 24px' }}>Notary professionals only.</p>

          {error && (
            <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Email address</label>
              <input
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 22 }}>
              <label style={labelStyle}>Password</label>
              <input
                type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                style={inputStyle}
              />
            </div>
            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? 'Signing in…' : 'Sign In →'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#64748b' }}>
          New notary?{' '}
          <a href="/notary-portal/register" style={{ color: '#0f2d52', fontWeight: 600, textDecoration: 'none' }}>Create account</a>
        </div>
        <div style={{ textAlign: 'center', marginTop: 8, fontSize: 13 }}>
          <a href="/notary-portal/client" style={{ color: '#64748b', textDecoration: 'none' }}>Looking for your signing? →</a>
        </div>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 };
const inputStyle: React.CSSProperties = { width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box' };
const btnStyle: React.CSSProperties = { width: '100%', background: '#0f2d52', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 600, cursor: 'pointer' };
