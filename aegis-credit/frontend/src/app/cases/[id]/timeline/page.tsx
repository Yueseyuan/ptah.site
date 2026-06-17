'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import CaseNav from '@/components/CaseNav';
import { listTimeline, buildTimeline, createTimelineEvent, deleteTimelineEvent } from '@/lib/api';

interface Event { id: number; event_type: string; event_date: string; title: string; description: string; source: string; }

export default function TimelinePage() {
  const { id } = useParams<{ id: string }>();
  const caseId = parseInt(id);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ event_type: 'account_opened', event_date: '', title: '', description: '', source: '' });
  const [success, setSuccess] = useState('');

  function load() { listTimeline(caseId).then(setEvents).finally(() => setLoading(false)); }
  useEffect(() => { load(); }, [caseId]);

  async function build() {
    setBuilding(true); setSuccess('');
    const r = await buildTimeline(caseId);
    setSuccess(`Built ${r.events_created} timeline events from tradelines.`);
    load();
    setBuilding(false);
  }

  async function addEvent(e: React.FormEvent) {
    e.preventDefault();
    await createTimelineEvent({ ...form, case_id: caseId });
    setForm({ event_type: 'account_opened', event_date: '', title: '', description: '', source: '' });
    setShowForm(false);
    load();
  }

  async function del(eventId: number) {
    await deleteTimelineEvent(eventId);
    load();
  }

  const typeColor: Record<string, string> = { account_opened: '#dbeafe', derogatory_reported: '#fee2e2', dispute_sent: '#fef3c7', response_received: '#d1fae5', payment: '#f0fdf4' };

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h1>Timeline</h1><p>Chronological history of account events</p></div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-outline" onClick={() => setShowForm(s => !s)}>{showForm ? 'Cancel' : '+ Add Event'}</button>
            <button className="btn btn-primary" onClick={build} disabled={building}>{building ? 'Building…' : 'Auto-Build'}</button>
          </div>
        </div>
        <CaseNav caseId={caseId} />

        {success && <div className="alert-success" style={{ marginBottom: 16 }}>{success}</div>}

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Add Timeline Event</h3>
            <form onSubmit={addEvent}>
              <div className="grid-2">
                <div className="form-group"><label>Event Type</label><select value={form.event_type} onChange={e => setForm(f => ({ ...f, event_type: e.target.value }))}>
                  <option value="account_opened">Account Opened</option>
                  <option value="derogatory_reported">Derogatory Reported</option>
                  <option value="dispute_sent">Dispute Sent</option>
                  <option value="response_received">Response Received</option>
                  <option value="payment">Payment</option>
                  <option value="other">Other</option>
                </select></div>
                <div className="form-group"><label>Date *</label><input type="date" required value={form.event_date} onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))} /></div>
                <div className="form-group"><label>Title *</label><input required value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
                <div className="form-group"><label>Source</label><input value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} /></div>
                <div className="form-group" style={{ gridColumn: '1/-1' }}><label>Description</label><textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></div>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">Add</button>
            </form>
          </div>
        )}

        {loading ? <div className="spinner" /> : events.length === 0 ? (
          <div className="card"><p className="empty">No timeline events yet. Click &quot;Auto-Build&quot; to generate from tradelines.</p></div>
        ) : (
          <div style={{ position: 'relative', paddingLeft: 24 }}>
            <div style={{ position: 'absolute', left: 8, top: 0, bottom: 0, width: 2, background: 'var(--border)' }} />
            {events.map(ev => (
              <div key={ev.id} style={{ position: 'relative', marginBottom: 16 }}>
                <div style={{ position: 'absolute', left: -20, top: 8, width: 12, height: 12, borderRadius: '50%', background: typeColor[ev.event_type] || '#e5e7eb', border: '2px solid var(--border)' }} />
                <div className="card" style={{ marginBottom: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: 'var(--muted)' }}>{ev.event_date}</span>
                        <span className="badge badge-pending" style={{ background: typeColor[ev.event_type] }}>{ev.event_type.replace(/_/g, ' ')}</span>
                        {ev.source && <span style={{ fontSize: 11, color: 'var(--muted)' }}>via {ev.source}</span>}
                      </div>
                      <div style={{ fontWeight: 600 }}>{ev.title}</div>
                      {ev.description && <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{ev.description}</p>}
                    </div>
                    <button className="btn btn-danger btn-sm" onClick={() => del(ev.id)}>×</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
