'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { registerUser, setToken } from '@/lib/api';
import { setPortalAuth } from '@/lib/portal-api';

export default function StaffRegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) { setError('Passwords do not match.'); return; }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setLoading(true);
    try {
      const { confirm, ...payload } = form;
      void confirm;
      const data = await registerUser({ ...payload, role: 'admin' });
      // Auto-login: store the token returned from register
      // Re-login to get a JWT since register doesn't return one
      const { loginUser } = await import('@/lib/api');
      const loginData = await loginUser(form.username, form.password);
      setToken(loginData.access_token);
      setPortalAuth(loginData.access_token, loginData.role);
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--bg)',
    }}>
      <div style={{ width: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚖</div>
          <h1 style={{ color: 'var(--navy)', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Create Admin Account
          </h1>
          <p style={{ color: 'var(--muted)', marginTop: 6, fontSize: 13 }}>
            First-time setup — creates the staff administrator account.
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit}>
            {error && <div className="alert-error" style={{ marginBottom: 14 }}>{error}</div>}
            <div className="form-group">
              <label>Username *</label>
              <input required value={form.username} onChange={e => set('username', e.target.value)} autoComplete="off" />
            </div>
            <div className="form-group">
              <label>Email *</label>
              <input required type="email" value={form.email} onChange={e => set('email', e.target.value)} autoComplete="off" />
            </div>
            <div className="form-group">
              <label>Full Name</label>
              <input value={form.full_name} onChange={e => set('full_name', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Password *</label>
              <input required type="password" minLength={8} value={form.password} onChange={e => set('password', e.target.value)} autoComplete="new-password" />
            </div>
            <div className="form-group">
              <label>Confirm Password *</label>
              <input required type="password" value={form.confirm} onChange={e => set('confirm', e.target.value)} autoComplete="new-password" />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 4 }} disabled={loading}>
              {loading ? 'Creating…' : 'Create Admin Account'}
            </button>
          </form>
          <div style={{ marginTop: 16, textAlign: 'center', fontSize: 12, color: 'var(--muted)' }}>
            Already have an account? <a href="/login" style={{ color: 'var(--primary)' }}>Sign in</a>
          </div>
        </div>

        <div className="disclosure-banner" style={{ marginTop: 16, textAlign: 'center', fontSize: 11 }}>
          This page is only functional when no admin account exists yet.
        </div>
      </div>
    </div>
  );
}
