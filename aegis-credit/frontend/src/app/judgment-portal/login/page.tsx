'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function JudgmentPortalLoginPage() {
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
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Invalid email or password.');
      }
      const data = await res.json();
      localStorage.setItem('judgment_token', data.access_token);
      localStorage.setItem('judgment_role', 'client');
      router.replace('/judgment-portal/dashboard');
    } catch (err: unknown) {
      setError((err as Error).message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#1c1917',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif', padding: 24,
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <a href="/judgment-portal" style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>⚖️</div>
            <div style={{ fontSize: 17, fontWeight: 800, color: '#fff' }}>Cruel &amp; Associates</div>
            <div style={{ fontSize: 11, color: '#C9A84C', letterSpacing: 1, textTransform: 'uppercase', marginTop: 2 }}>Recovery Portal</div>
          </a>
        </div>

        <div style={{ background: '#fff', borderRadius: 14, padding: '32px 28px', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1c1917', margin: '0 0 6px' }}>Sign in to your account</h2>
          <p style={{ fontSize: 13, color: '#64748b', margin: '0 0 24px' }}>Track your recovery case and submit new claims.</p>

          {error && (
            <div style={{ background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', marginBottom: 18, fontSize: 13 }}>{error}</div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 14 }}>
              <label style={labelStyle}>Email address</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com" style={inputStyle} />
            </div>
            <div style={{ marginBottom: 22 }}>
              <label style={labelStyle}>Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••" style={inputStyle} />
            </div>
            <button type="submit" disabled={loading} style={btnStyle}>
              {loading ? 'Signing in…' : 'Sign In →'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#57534e' }}>
          New client?{' '}
          <a href="/judgment-portal/register" style={{ color: '#C9A84C', fontWeight: 600, textDecoration: 'none' }}>Create account</a>
        </div>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 };
const inputStyle: React.CSSProperties = { width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box' };
const btnStyle: React.CSSProperties = { width: '100%', background: '#C9A84C', color: '#1c1917', border: 'none', borderRadius: 8, padding: '12px 0', fontSize: 15, fontWeight: 800, cursor: 'pointer' };
