import Link from 'next/link';

export default function NotFound() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6fa' }}>
      <div style={{ textAlign: 'center', maxWidth: 400 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>⚖</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: '#1e2d5a', marginBottom: 8 }}>Page Not Found</h1>
        <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 14 }}>
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link href="/dashboard" style={{ display: 'inline-block', padding: '10px 24px', background: '#1e2d5a', color: 'white', borderRadius: 8, textDecoration: 'none', fontSize: 14, fontWeight: 500 }}>
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
