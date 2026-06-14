'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function doLogin(emailVal: string, passVal: string) {
    setError('');
    setLoading(true);
    try {
      const data = await login(emailVal, passVal);
      localStorage.setItem('ca_token', data.access_token);
      localStorage.setItem('ca_user', JSON.stringify(data.user));
      router.push('/dashboard');
    } catch (err: any) {
      if (!err.response) {
        setError('Cannot reach backend at localhost:8000 — make sure the server is running.');
      } else {
        setError(err.response?.data?.detail || `Server error ${err.response?.status}`);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await doLogin(email, password);
  }

  async function handleDevAccess() {
    await doLogin('admin@cruelandassociates.site', 'CruelAdmin2024!');
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)',
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            background: 'var(--navy)', color: 'white', borderRadius: 8,
            padding: '20px 24px', marginBottom: 12,
          }}>
            <h1 style={{ fontSize: 20, fontWeight: 700 }}>Cruel & Associates</h1>
            <p style={{ color: 'var(--gold)', fontSize: 11, marginTop: 4 }}>
              CA Engine — Staff Portal
            </p>
          </div>
        </div>
        <div className="card">
          <h2 style={{ fontSize: 18, color: 'var(--navy)', marginBottom: 20, fontWeight: 700 }}>
            Sign In
          </h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="staff@cruelandassociates.site"
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            {error && (
              <p className="error-msg" style={{ marginBottom: 12, fontSize: 12 }}>{error}</p>
            )}
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8, textAlign: 'center' }}>
              Local access
            </p>
            <button
              onClick={handleDevAccess}
              disabled={loading}
              style={{
                width: '100%',
                padding: '10px',
                background: '#f0f4ff',
                border: '1px solid #c0cdf0',
                borderRadius: 6,
                color: '#1a3a8f',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {loading ? 'Signing in…' : 'Quick Admin Access'}
            </button>
          </div>
        </div>
        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--muted)', marginTop: 16 }}>
          Cruel & Associates is not a law firm and does not provide legal advice.
        </p>
      </div>
    </div>
  );
}
