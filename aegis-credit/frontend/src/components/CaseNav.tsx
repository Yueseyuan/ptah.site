'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS = [
  { href: '', label: 'Dashboard' },
  { href: '/reports', label: 'Reports' },
  { href: '/tradelines', label: 'Tradelines' },
  { href: '/comparison', label: 'Comparison' },
  { href: '/findings', label: 'Findings' },
  { href: '/metro2', label: 'Metro 2' },
  { href: '/evidence', label: 'Evidence' },
  { href: '/court-records', label: 'Court Records' },
  { href: '/timeline', label: 'Timeline' },
  { href: '/strategy', label: 'Strategy' },
  { href: '/disputes', label: 'Disputes' },
  { href: '/outcomes', label: 'Outcomes' },
];

export default function CaseNav({ caseId }: { caseId: number }) {
  const path = usePathname();
  const base = `/cases/${caseId}`;
  return (
    <div className="case-nav">
      {TABS.map((t) => {
        const href = base + t.href;
        const isActive = t.href === '' ? path === base : path.startsWith(href);
        return (
          <Link key={href} href={href} className={isActive ? 'active' : ''}>
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
