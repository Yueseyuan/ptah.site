'use client';
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { listTemplates, createTemplate, updateTemplate, deleteTemplate, seedTemplates, previewTemplate } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Template {
  id: number;
  name: string;
  description: string;
  division_slug: string;
  category: string;
  template_type: string;
  content: string;
  variables: string[];
}

interface TemplateForm {
  name: string;
  description: string;
  division_slug: string;
  category: string;
  template_type: string;
  content: string;
  variables: string; // comma-separated string in the UI
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DIVISIONS = ['notary', 'credit', 'criminal', 'document', 'judgment', 'consulting'];
const DIVISION_LABELS: Record<string, string> = {
  notary: 'Mobile Notary', credit: 'Credit Restoration', criminal: 'Criminal Record Relief',
  document: 'Document Preparation', judgment: 'Judgment & Asset Recovery', consulting: 'Business Consulting',
};
const CATEGORIES = ['Dispute Letter', 'Authorization', 'Agreement', 'Notice', 'Report', 'Other'];
const TEMPLATE_TYPES = ['document', 'letter', 'email', 'contract', 'report', 'other'];

const DIVISION_COLORS: Record<string, { bg: string; color: string }> = {
  notary:    { bg: '#dbeafe', color: '#1e40af' },
  credit:    { bg: '#d1fae5', color: '#065f46' },
  criminal:  { bg: '#fef3c7', color: '#92400e' },
  document:  { bg: '#ede9fe', color: '#5b21b6' },
  judgment:  { bg: '#fee2e2', color: '#991b1b' },
  consulting:{ bg: '#f3f4f6', color: '#374151' },
};

const EMPTY_FORM: TemplateForm = {
  name: '', description: '', division_slug: '', category: '', template_type: 'document', content: '', variables: '',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function DivisionBadge({ division }: { division: string }) {
  const s = DIVISION_COLORS[division] || { bg: '#f3f4f6', color: '#374151' };
  return (
    <span style={{ background: s.bg, color: s.color, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 600 }}>
      {DIVISION_LABELS[division] || division}
    </span>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function Modal({ title, onClose, wide, children }: { title: string; onClose: () => void; wide?: boolean; children: React.ReactNode }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 40, paddingBottom: 40 }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: 'white', borderRadius: 'var(--radius)', width: wide ? 860 : 640, maxWidth: '96vw', maxHeight: '90vh', overflowY: 'auto', padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--navy)' }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--muted)', lineHeight: 1 }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ─── Template Card ────────────────────────────────────────────────────────────

function TemplateCard({ tpl, onEdit, onDelete }: { tpl: Template; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--navy)', marginBottom: 4 }}>{tpl.name}</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            {tpl.division_slug && <DivisionBadge division={tpl.division_slug} />}
            {tpl.category && (
              <span style={{ fontSize: 11, color: 'var(--muted)', background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 3, padding: '1px 6px' }}>
                {tpl.category}
              </span>
            )}
            {tpl.template_type && (
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                [{tpl.template_type}]
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button className="btn btn-outline btn-sm" onClick={onEdit}>Edit</button>
          <button
            onClick={onDelete}
            style={{ padding: '4px 10px', fontSize: 12, background: '#fee2e2', color: '#991b1b', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
            Delete
          </button>
        </div>
      </div>

      {tpl.description && (
        <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>{tpl.description}</p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: 'var(--muted)', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
        <span>
          <strong style={{ color: 'var(--navy)' }}>{(tpl.variables || []).length}</strong> variable{(tpl.variables || []).length !== 1 ? 's' : ''}
        </span>
        {(tpl.variables || []).length > 0 && (
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {(tpl.variables || []).map(v => <code key={v} style={{ marginRight: 4 }}>{`{{${v}}}`}</code>)}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDivision, setFilterDivision] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState<Template | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewing, setPreviewing] = useState(false);

  function fetchTemplates() {
    setLoading(true);
    listTemplates().then(setTemplates).finally(() => setLoading(false));
  }

  useEffect(() => { fetchTemplates(); }, []);

  // Filtered
  const visible = templates.filter(t => {
    if (filterDivision && t.division_slug !== filterDivision) return false;
    if (filterCategory && t.category !== filterCategory) return false;
    return true;
  });

  function openCreate() {
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setPreviewHtml('');
    setShowModal(true);
  }

  function openEdit(tpl: Template) {
    setEditTarget(tpl);
    setForm({
      name: tpl.name || '',
      description: tpl.description || '',
      division: tpl.division || '',
      category: tpl.category || '',
      template_type: tpl.template_type || 'document',
      content: tpl.content || '',
      variables: (tpl.variables || []).join(', '),
    });
    setFormError('');
    setPreviewHtml('');
    setShowModal(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    setSaving(true);
    setFormError('');
    const vars = form.variables
      .split(',')
      .map(v => v.trim())
      .filter(Boolean);
    const payload = { ...form, variables: vars };
    try {
      if (editTarget) {
        await updateTemplate(editTarget.id, payload);
        setSuccess('Template updated.');
      } else {
        await createTemplate(payload);
        setSuccess('Template created.');
      }
      setShowModal(false);
      fetchTemplates();
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setFormError(e.response?.data?.detail || 'Failed to save template.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this template? This cannot be undone.')) return;
    try {
      await deleteTemplate(id);
      setTemplates(prev => prev.filter(t => t.id !== id));
      setSuccess('Template deleted.');
      setTimeout(() => setSuccess(''), 3000);
    } catch {
      alert('Failed to delete template.');
    }
  }

  async function handleSeed() {
    if (!confirm('Seed default templates? This may add duplicates if defaults already exist.')) return;
    setSeeding(true);
    try {
      const result = await seedTemplates();
      const count = result?.created ?? result?.count ?? (Array.isArray(result) ? result.length : '?');
      setSuccess(`Seeded ${count} default template(s).`);
      fetchTemplates();
      setTimeout(() => setSuccess(''), 5000);
    } catch {
      alert('Failed to seed templates.');
    } finally {
      setSeeding(false);
    }
  }

  async function handlePreview() {
    if (!editTarget) return;
    setPreviewing(true);
    setPreviewHtml('');
    try {
      const result = await previewTemplate(editTarget.id);
      setPreviewHtml(result?.rendered_text || result?.preview || result?.content || JSON.stringify(result));
    } catch {
      setPreviewHtml('Preview unavailable.');
    } finally {
      setPreviewing(false);
    }
  }

  const field = (k: keyof TemplateForm) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(prev => ({ ...prev, [k]: e.target.value }));

  // Unique divisions / categories for filters (from loaded data)
  const availableDivisions = Array.from(new Set(templates.map(t => t.division_slug).filter(Boolean)));
  const availableCategories = Array.from(new Set(templates.map(t => t.category).filter(Boolean)));

  return (
    <div className="main-layout">
      <Sidebar />
      <main className="main-content">

        {/* Header */}
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Document Templates</h1>
            <p>{visible.length} of {templates.length} template{templates.length !== 1 ? 's' : ''}</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-outline" onClick={handleSeed} disabled={seeding}>
              {seeding ? 'Seeding…' : 'Seed Defaults'}
            </button>
            <button className="btn btn-primary" onClick={openCreate}>+ New Template</button>
          </div>
        </div>

        {success && <div className="alert alert-success">{success}</div>}

        {/* Filters */}
        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--muted)', whiteSpace: 'nowrap' }}>Division:</label>
            <select
              value={filterDivision}
              onChange={e => setFilterDivision(e.target.value)}
              style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 13 }}>
              <option value="">All divisions</option>
              {availableDivisions.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--muted)', whiteSpace: 'nowrap' }}>Category:</label>
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value)}
              style={{ padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 13 }}>
              <option value="">All categories</option>
              {availableCategories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          {(filterDivision || filterCategory) && (
            <button
              className="btn btn-outline btn-sm"
              onClick={() => { setFilterDivision(''); setFilterCategory(''); }}>
              Clear filters
            </button>
          )}
        </div>

        {/* Template grid */}
        {loading ? (
          <div className="spinner" />
        ) : visible.length === 0 ? (
          <div className="card">
            <p className="empty">
              {templates.length === 0
                ? 'No templates yet. Click "Seed Defaults" to add starter templates, or create your own.'
                : 'No templates match the selected filters.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
            {visible.map(tpl => (
              <TemplateCard
                key={tpl.id}
                tpl={tpl}
                onEdit={() => openEdit(tpl)}
                onDelete={() => handleDelete(tpl.id)}
              />
            ))}
          </div>
        )}

        {/* Create / Edit Modal */}
        {showModal && (
          <Modal title={editTarget ? 'Edit Template' : 'New Template'} onClose={() => setShowModal(false)} wide>
            {formError && <div className="alert alert-error">{formError}</div>}
            <form onSubmit={handleSave}>

              <div className="grid-2">
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Name *</label>
                  <input required type="text" value={form.name} onChange={field('name')} placeholder="e.g. FCRA Dispute Letter — Equifax" />
                </div>

                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>Description</label>
                  <input type="text" value={form.description} onChange={field('description')} placeholder="Brief description of when to use this template…" />
                </div>

                <div className="form-group">
                  <label>Division</label>
                  <select value={form.division_slug} onChange={field('division_slug')}>
                    <option value="">— Select division —</option>
                    {DIVISIONS.map(d => <option key={d} value={d}>{DIVISION_LABELS[d] || d}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label>Category</label>
                  <select value={form.category} onChange={field('category')}>
                    <option value="">— Select category —</option>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label>Template Type</label>
                  <select value={form.template_type} onChange={field('template_type')}>
                    {TEMPLATE_TYPES.map(t => <option key={t} value={t} style={{ textTransform: 'capitalize' }}>{t}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label>Variables (comma-separated)</label>
                  <input
                    type="text"
                    value={form.variables}
                    onChange={field('variables')}
                    placeholder="client_name, date, creditor, account_number"
                  />
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                    Use <code>{'{{variable_name}}'}</code> syntax in the content below.
                  </div>
                </div>
              </div>

              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <label style={{ margin: 0 }}>Content</label>
                  {editTarget && (
                    <button type="button" className="btn btn-outline btn-sm" onClick={handlePreview} disabled={previewing}>
                      {previewing ? 'Generating…' : 'Preview'}
                    </button>
                  )}
                </div>
                <textarea
                  rows={14}
                  value={form.content}
                  onChange={field('content')}
                  placeholder={`Enter your template content here.\n\nUse {{variable_name}} for dynamic fields.\n\nExample:\nDear {{client_name}},\n\nThis letter is to dispute the following account: {{account_number}}\n\nSincerely,\n{{firm_name}}`}
                  style={{ fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6 }}
                />
              </div>

              {/* Preview panel */}
              {previewHtml && (
                <div style={{ marginBottom: 16, border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                  <div style={{ background: '#f5f6fa', padding: '8px 12px', fontSize: 12, fontWeight: 600, color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}>
                    Preview
                  </div>
                  <div style={{ padding: 16, fontSize: 13, whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: 1.6, maxHeight: 300, overflowY: 'auto' }}>
                    {previewHtml}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 12 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editTarget ? 'Save Changes' : 'Create Template'}
                </button>
              </div>
            </form>
          </Modal>
        )}

      </main>
    </div>
  );
}
