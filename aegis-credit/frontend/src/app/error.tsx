'use client';
import { useEffect } from 'react';
import Link from 'next/link';

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error('Application error:', error);
  }, [error]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6fa' }}>
      <div style={{ textAlign: 'center', maxWidth: 440 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>⚠</div>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1e2d5a', marginBottom: 8 }}>Something Went Wrong</h1>
        <p style={{ color: '#6b7280', marginBottom: 8, fontSize: 14 }}>
          An unexpected error occurred. Please try again.
        </p>
        {error.message && (
          <p style={{ fontSize: 12, color: '#9ca3af', fontFamily: 'monospace', marginBottom: 24, background: '#f3f4f6', padding: '8px 12px', borderRadius: 6 }}>
            {error.message}
          </p>
        )}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button onClick={reset} style={{ padding: '10px 20px', background: '#1e2d5a', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 500 }}>
            Try Again
          </button>
          <Link href="/dashboard" style={{ padding: '10px 20px', background: 'white', color: '#1e2d5a', border: '1px solid #e5e7eb', borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 500 }}>
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
