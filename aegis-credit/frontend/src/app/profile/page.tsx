'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getMe, updateMyProfile } from '@/lib/api';

interface UserProfile { id: number; username: string; email: string; full_name: string | null; role: string; is_active: boolean; created_at: string | null; }

export default function ProfilePage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Profile form
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');

  // Password form
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSuccess, setPwSuccess] = useState('');
  const [pwError, setPwError] = useState('');

  useEffect(() => {
    getMe().then(u => {
      setUser(u);
      setFullName(u.full_name || '');
      setEmail(u.email || '');
    }).finally(() => setLoading(false));
  }, []);

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setProfileSaving(true); setProfileError(''); setProfileSuccess('');
    try {
      const updated = await updateMyProfile({ full_name: fullName, email });
      setUser(updated);
      setProfileSuccess('Profile updated.');
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setProfileError(e.response?.data?.detail || 'Failed to update profile.');
    } finally { setProfileSaving(false); }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwError(''); setPwSuccess('');
    if (newPw !== confirmPw) { setPwError('New passwords do not match.'); return; }
    if (newPw.length < 8) { setPwError('Password must be at least 8 characters.'); return; }
    setPwSaving(true);
    try {
      await updateMyProfile({ current_password: currentPw, new_password: newPw });
      setPwSuccess('Password changed successfully.');
      setCurrentPw(''); setNewPw(''); setConfirmPw('');
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setPwError(e.response?.data?.detail || 'Failed to change password.');
    } finally { setPwSaving(false); }
  }

  if (loading) return <div className="main-layout"><Sidebar /><main className="main-content"><div className="spinner" /></main></div>;

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>My Profile</h1>
          {user && <p>@{user.username} · <span style={{ textTransform: 'capitalize' }}>{user.role}</span>{user.created_at ? ` · Joined ${new Date(user.created_at).toLocaleDateString()}` : ''}</p>}
        </div>

        {/* Profile info */}
        <div className="card" style={{ marginBottom: 20 }}>
          <h3>Profile Settings</h3>
          {profileError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{profileError}</div>}
          {profileSuccess && <div className="alert alert-success" style={{ marginBottom: 12 }}>{profileSuccess}</div>}
          <form onSubmit={saveProfile}>
            <div className="grid-2">
              <div className="form-group">
                <label>Full Name</label>
                <input value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Your full name" />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 4 }}>
              <button type="submit" className="btn btn-primary" disabled={profileSaving}>
                {profileSaving ? 'Saving…' : 'Save Changes'}
              </button>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>Username: <code>{user?.username}</code> (cannot be changed)</span>
            </div>
          </form>
        </div>

        {/* Change password */}
        <div className="card">
          <h3>Change Password</h3>
          {pwError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{pwError}</div>}
          {pwSuccess && <div className="alert alert-success" style={{ marginBottom: 12 }}>{pwSuccess}</div>}
          <form onSubmit={changePassword}>
            <div style={{ maxWidth: 360, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group">
                <label>Current Password</label>
                <input type="password" value={currentPw} onChange={e => setCurrentPw(e.target.value)} required autoComplete="current-password" />
              </div>
              <div className="form-group">
                <label>New Password</label>
                <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)} required autoComplete="new-password" minLength={8} />
              </div>
              <div className="form-group">
                <label>Confirm New Password</label>
                <input type="password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)} required autoComplete="new-password" />
              </div>
              <button type="submit" className="btn btn-primary" disabled={pwSaving} style={{ alignSelf: 'flex-start' }}>
                {pwSaving ? 'Changing…' : 'Change Password'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
