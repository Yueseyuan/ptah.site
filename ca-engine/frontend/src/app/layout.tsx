import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CA Engine — Cruel & Associates',
  description: 'Administrative services management platform for Cruel & Associates.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
