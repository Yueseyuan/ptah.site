'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    localStorage.setItem('ca_token', 'dev');
    localStorage.setItem('ca_user', JSON.stringify({
      id: 1, email: 'admin@cruelandassociates.site',
      full_name: 'System Admin', role: 'admin', is_active: true,
    }));
    router.replace('/dashboard');
  }, [router]);

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--bg)',
    }}>
      <div style={{ textAlign: 'center', color: 'var(--muted)' }}>
        <div className="spinner" style={{ margin: '0 auto 16px' }} />
        <p>Entering CA Engine…</p>
      </div>
    </div>
  );
}
