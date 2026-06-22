'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { portalLogin, setPortalAuth } from '@/lib/portal-api';

export default function PortalLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await portalLogin(username, password);
      setPortalAuth(data.access_token, data.role);
      if (data.role === 'client') {
        router.push('/portal/dashboard');
      } else {
        router.push('/cases');
      }
    } catch {
      setError('Invalid username or password.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#f5f7fa',
    }}>
      <div style={{ width: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>⚖</div>
          <h1 style={{ color: '#0a2540', fontSize: 24, fontWeight: 700, margin: 0 }}>
            Cruel &amp; Associates
          </h1>
          <p style={{ color: '#64748b', marginTop: 6, fontSize: 14 }}>
            Client Portal — Sign In
          </p>
        </div>

        <div style={{
          background: '#fff', borderRadius: 12, padding: 32,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        }}>
          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{
                background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca',
                borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 14,
              }}>
                {error}
              </div>
            )}
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                style={inputStyle}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              style={btnStyle}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#64748b' }}>
            <a href="/portal/forgot-password" style={{ color: '#64748b', textDecoration: 'none' }}>
              Forgot your password?
            </a>
          </div>
          <div style={{ textAlign: 'center', marginTop: 12, fontSize: 13, color: '#64748b' }}>
            New client?{' '}
            <a href="/portal/register" style={{ color: '#1d4ed8', fontWeight: 600, textDecoration: 'none' }}>
              Create an account
            </a>
          </div>
        </div>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 11, color: '#94a3b8' }}>
          For assistance, contact your case manager directly.
        </p>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #d1d5db',
  borderRadius: 8,
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
};

const btnStyle: React.CSSProperties = {
  width: '100%',
  background: '#0a2540',
  color: '#fff',
  border: 'none',
  borderRadius: 8,
  padding: '12px 0',
  fontSize: 15,
  fontWeight: 600,
  cursor: 'pointer',
};
