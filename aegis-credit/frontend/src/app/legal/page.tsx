'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listFederalLaws, listAgencyGuidance, listStateLaws, listCaseLaw, searchLegal } from '@/lib/api';

type Tab = 'federal' | 'guidance' | 'state' | 'cases';

interface FederalLaw { id: number; short_name: string; title: string; citation: string; section: string; summary: string; effective_date: string; category: string; source_url: string; }
interface Guidance { id: number; agency: string; document_name: string; publication_date: string; topic: string; summary: string; source_url: string; }
interface StateLaw { id: number; state: string; statute: string; citation: string; topic: string; effective_date: string; summary: string; source_url: string; }
interface CaseLawItem { id: number; case_name: string; citation: string; court: string; jurisdiction: string; year: number; topic: string; holding_summary: string; legal_principle: string; relevance_tags: string; source_url: string; }

export default function LegalPage() {
  const [tab, setTab] = useState<Tab>('federal');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [federal, setFederal] = useState<FederalLaw[]>([]);
  const [guidance, setGuidance] = useState<Guidance[]>([]);
  const [stateLaws, setStateLaws] = useState<StateLaw[]>([]);
  const [caseLaw, setCaseLaw] = useState<CaseLawItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setLoading(true);
    const s = debouncedSearch || undefined;
    Promise.all([
      listFederalLaws({ search: s }),
      listAgencyGuidance({ search: s }),
      listStateLaws({ search: s }),
      listCaseLaw({ search: s }),
    ]).then(([f, g, sl, cl]) => {
      setFederal(f); setGuidance(g); setStateLaws(sl); setCaseLaw(cl);
    }).finally(() => setLoading(false));
  }, [debouncedSearch]);

  const categories = Array.from(new Set(federal.map(f => f.category))).sort();

  const tabStyle = (t: Tab) => ({
    padding: '8px 16px',
    border: 'none',
    borderBottom: tab === t ? '2px solid #1e40af' : '2px solid transparent',
    background: 'none',
    fontWeight: tab === t ? 700 : 400,
    color: tab === t ? '#1e40af' : '#6b7280',
    cursor: 'pointer',
    fontSize: 14,
  });

  const toggle = (key: string) => setExpanded(e => ({ ...e, [key]: !e[key] }));

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1>Legal Knowledge Engine</h1>
          <p>Federal laws, agency guidance, state statutes, and case law reference library</p>
        </div>

        <div className="disclosure-banner" style={{ marginBottom: 16 }}>
          For research support only. Not legal advice. Attorney review required before any action based on this information.
        </div>

        <div className="card" style={{ marginBottom: 16 }}>
          <input
            className="form-input"
            placeholder="Search all legal resources…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: 20, display: 'flex', gap: 4 }}>
          <button style={tabStyle('federal')} onClick={() => setTab('federal')}>Federal Laws ({federal.length})</button>
          <button style={tabStyle('guidance')} onClick={() => setTab('guidance')}>Agency Guidance ({guidance.length})</button>
          <button style={tabStyle('state')} onClick={() => setTab('state')}>State Laws ({stateLaws.length})</button>
          <button style={tabStyle('cases')} onClick={() => setTab('cases')}>Case Law ({caseLaw.length})</button>
        </div>

        {loading ? <p>Loading…</p> : (
          <>
            {tab === 'federal' && (
              categories.length === 0 ? <p style={{ color: '#6b7280' }}>No federal laws found.</p> :
              categories.map(cat => (
                <div key={cat} style={{ marginBottom: 24 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#6b7280', marginBottom: 12 }}>{cat.replace(/_/g, ' ')}</h3>
                  {federal.filter(f => f.category === cat).map(law => (
                    <div key={law.id} className="card" style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', cursor: 'pointer' }} onClick={() => toggle(`f-${law.id}`)}>
                        <div>
                          <span style={{ background: '#1e40af', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, marginRight: 8 }}>{law.short_name}</span>
                          <span style={{ fontWeight: 600, fontSize: 14 }}>{law.title}</span>
                          {law.section && <span style={{ marginLeft: 8, fontSize: 13, color: '#6b7280' }}>{law.section}</span>}
                        </div>
                        <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded[`f-${law.id}`] ? '▲' : '▼'}</span>
                      </div>
                      <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>{law.citation}</p>
                      {expanded[`f-${law.id}`] && (
                        <div style={{ marginTop: 10 }}>
                          <p style={{ margin: '0 0 8px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{law.summary}</p>
                          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6b7280' }}>
                            {law.effective_date && <span>Effective: {law.effective_date}</span>}
                            {law.source_url && <a href={law.source_url} target="_blank" rel="noreferrer" style={{ color: '#1e40af' }}>Source ↗</a>}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))
            )}

            {tab === 'guidance' && (
              guidance.length === 0 ? <p style={{ color: '#6b7280' }}>No agency guidance found.</p> :
              guidance.map(g => (
                <div key={g.id} className="card" style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', cursor: 'pointer' }} onClick={() => toggle(`g-${g.id}`)}>
                    <div>
                      <span style={{ background: '#065f46', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, marginRight: 8 }}>{g.agency}</span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{g.document_name}</span>
                    </div>
                    <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded[`g-${g.id}`] ? '▲' : '▼'}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>{g.topic} · {g.publication_date}</p>
                  {expanded[`g-${g.id}`] && (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ margin: '0 0 8px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{g.summary}</p>
                      {g.source_url && <a href={g.source_url} target="_blank" rel="noreferrer" style={{ color: '#1e40af', fontSize: 12 }}>Source ↗</a>}
                    </div>
                  )}
                </div>
              ))
            )}

            {tab === 'state' && (
              stateLaws.length === 0 ? <p style={{ color: '#6b7280' }}>No state laws found.</p> :
              stateLaws.map(s => (
                <div key={s.id} className="card" style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', cursor: 'pointer' }} onClick={() => toggle(`s-${s.id}`)}>
                    <div>
                      <span style={{ background: '#7c3aed', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700, marginRight: 8 }}>{s.state}</span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{s.statute}</span>
                    </div>
                    <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded[`s-${s.id}`] ? '▲' : '▼'}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>{s.citation} · {s.topic}</p>
                  {expanded[`s-${s.id}`] && (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ margin: '0 0 8px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{s.summary}</p>
                      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6b7280' }}>
                        {s.effective_date && <span>Effective: {s.effective_date}</span>}
                        {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" style={{ color: '#1e40af' }}>Source ↗</a>}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}

            {tab === 'cases' && (
              caseLaw.length === 0 ? <p style={{ color: '#6b7280' }}>No case law found.</p> :
              caseLaw.map(c => (
                <div key={c.id} className="card" style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', cursor: 'pointer' }} onClick={() => toggle(`c-${c.id}`)}>
                    <div>
                      <span style={{ fontWeight: 700, fontSize: 14 }}>{c.case_name}</span>
                      <span style={{ marginLeft: 8, fontSize: 12, color: '#6b7280' }}>{c.year} · {c.court}</span>
                    </div>
                    <span style={{ color: '#6b7280', fontSize: 12 }}>{expanded[`c-${c.id}`] ? '▲' : '▼'}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#6b7280' }}>{c.citation} · {c.topic}</p>
                  {expanded[`c-${c.id}`] && (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: '#374151' }}>Holding</p>
                      <p style={{ margin: '0 0 12px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{c.holding_summary}</p>
                      {c.legal_principle && (
                        <>
                          <p style={{ margin: '0 0 4px', fontSize: 13, fontWeight: 600, color: '#374151' }}>Legal Principle</p>
                          <p style={{ margin: '0 0 12px', fontSize: 13, color: '#374151', lineHeight: 1.6 }}>{c.legal_principle}</p>
                        </>
                      )}
                      <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#6b7280', alignItems: 'center' }}>
                        <span>Jurisdiction: {c.jurisdiction}</span>
                        {c.source_url && <a href={c.source_url} target="_blank" rel="noreferrer" style={{ color: '#1e40af' }}>Source ↗</a>}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </>
        )}
      </main>
    </div>
  );
}
