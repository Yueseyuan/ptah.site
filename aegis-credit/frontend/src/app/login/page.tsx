'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loginUser, setToken, getToken } from '@/lib/api';
import { setPortalAuth, getPortalRole, clearPortalAuth } from '@/lib/portal-api';

const STAFF_ROLES = ['admin', 'investigator', 'reviewer', 'readonly'];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Local desktop mode: auto-login without credentials
    if (process.env.NEXT_PUBLIC_DEV_MODE === 'true') {
      setLoading(true);
      loginUser('dev_admin', 'dev').then(data => {
        clearPortalAuth();
        setToken(data.access_token);
        setPortalAuth(data.access_token, data.role || 'admin');
        router.replace('/cases');
      }).catch((err: unknown) => {
        setLoading(false);
        setError('Dev auto-login failed — is the local backend running on port 8082?');
        console.error('Dev auto-login error:', err);
      });
      return;
    }
    const token = getToken();
    const role = getPortalRole();
    // Only auto-redirect if the stored token belongs to a staff role.
    // A client-role token (from portal registration) should NOT skip the login form.
    if (token && role && STAFF_ROLES.includes(role)) {
      router.replace('/cases');
    } else if (token && (!role || !STAFF_ROLES.includes(role))) {
      // Clear a stale client token so the login form is usable.
      clearPortalAuth();
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await loginUser(username, password);
      // Clear any stale keys before writing fresh ones
      clearPortalAuth();
      setToken(data.access_token);
      setPortalAuth(data.access_token, data.role || '');
      if (data.role === 'client') {
        router.push('/portal/dashboard');
      } else {
        router.push('/cases');
      }
    } catch (err: unknown) {
      const e = err as Error & { response?: { status: number } };
      if (e.response?.status === 401 || e.response?.status === 400) {
        setError('Invalid username or password.');
      } else {
        setError(e.message || 'Sign in failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--bg)',
    }}>
      <div style={{ width: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚖</div>
          <h1 style={{ color: 'var(--navy)', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Aegis Credit Intelligence
          </h1>
          <p style={{ color: 'var(--muted)', marginTop: 6, fontSize: 13 }}>
            Investigation &amp; compliance platform
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 18 }}>Sign In</h3>
          <form onSubmit={handleSubmit}>
            {error && <div className="alert-error" style={{ marginBottom: 14 }}>{error}</div>}
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
          <div style={{ marginTop: 14, textAlign: 'center', fontSize: 12, color: 'var(--muted)' }}>
            First time? <a href="/register" style={{ color: 'var(--primary)' }}>Create admin account</a>
          </div>
        </div>

        <div className="disclosure-banner" style={{ marginTop: 16, textAlign: 'center', fontSize: 11 }}>
          Human review required for all findings. Not legal advice.
        </div>
      </div>
    </div>
  );
}
