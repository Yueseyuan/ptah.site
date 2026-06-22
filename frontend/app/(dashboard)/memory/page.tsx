"use client";

import { useEffect, useState } from "react";
import { memoryApi, MemoryEntry, MemoryCollection } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Brain, Search, X } from "lucide-react";

const CONTENT_TYPES = ["text", "code", "url", "file", "json"] as const;

export default function MemoryPage() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [collections, setCollections] = useState<MemoryCollection[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [contentType, setContentType] = useState<string>("text");
  const [collectionId, setCollectionId] = useState<number | undefined>();
  const [importance, setImportance] = useState("0.5");
  const [creating, setCreating] = useState(false);

  async function load(query?: string) {
    try {
      const [e, c] = await Promise.all([
        query ? memoryApi.searchEntries(query) : memoryApi.listEntries(),
        memoryApi.listCollections(),
      ]);
      setEntries(e);
      setCollections(c);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await load(q.trim() || undefined);
  }

  async function create() {
    if (!title.trim() || !content.trim()) return;
    setCreating(true);
    try {
      await memoryApi.createEntry({
        title: title.trim(),
        content: content.trim(),
        content_type: contentType,
        collection_id: collectionId,
        importance_score: parseFloat(importance) || 0.5,
      });
      setTitle(""); setContent(""); setShowCreate(false);
      load();
    } finally {
      setCreating(false);
    }
  }

  const typeColors: Record<string, string> = {
    text: "default",
    code: "purple",
    url: "info",
    file: "warn",
    json: "success",
  };

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">Memory</h1>
          <p className="text-sm text-[--text-secondary] mt-0.5">{entries.length} entries across {collections.length} collections</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New Entry
        </Button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search memory entries..."
          className="flex-1"
        />
        <Button type="submit" variant="secondary">
          <Search size={14} /> Search
        </Button>
        {q && <Button type="button" variant="ghost" onClick={() => { setQ(""); load(); }}><X size={14} /></Button>}
      </form>

      {/* Create form */}
      {showCreate && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[--text-primary]">New Memory Entry</h3>
            <button onClick={() => setShowCreate(false)} className="text-[--text-muted] hover:text-[--text-primary]"><X size={14} /></button>
          </div>
          <div className="space-y-3">
            <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What is this about?" />
            <Textarea label="Content" value={content} onChange={(e) => setContent(e.target.value)} rows={4} placeholder="Content..." />
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-[--text-secondary]">Type</label>
                <select
                  value={contentType}
                  onChange={(e) => setContentType(e.target.value)}
                  className="bg-[--surface-2] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]"
                >
                  {CONTENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-[--text-secondary]">Collection</label>
                <select
                  value={collectionId ?? ""}
                  onChange={(e) => setCollectionId(e.target.value ? parseInt(e.target.value) : undefined)}
                  className="bg-[--surface-2] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]"
                >
                  <option value="">None</option>
                  {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <Input label="Importance (0–1)" value={importance} onChange={(e) => setImportance(e.target.value)} type="number" min="0" max="1" step="0.1" />
            </div>
            <div className="flex gap-2">
              <Button onClick={create} loading={creating} size="sm">Save</Button>
              <Button variant="ghost" onClick={() => setShowCreate(false)} size="sm">Cancel</Button>
            </div>
          </div>
        </Card>
      )}

      {/* Entries */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="bg-[--surface] border border-[--border] rounded-xl h-24 animate-pulse" />)}
        </div>
      ) : entries.length === 0 ? (
        <Card className="text-center py-12">
          <Brain size={32} className="text-[--text-muted] mx-auto mb-3" />
          <p className="text-sm text-[--text-secondary]">No memory entries yet.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <Card key={entry.id}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium text-[--text-primary] truncate">{entry.title}</p>
                    <Badge variant={(typeColors[entry.content_type] ?? "default") as Parameters<typeof Badge>[0]["variant"]}>
                      {entry.content_type}
                    </Badge>
                  </div>
                  <p className="text-xs text-[--text-secondary] line-clamp-2">{entry.content}</p>
                  <p className="text-[10px] text-[--text-muted] mt-2">
                    Importance: {(entry.importance_score * 100).toFixed(0)}% · {new Date(entry.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="w-8 h-1.5 rounded-full bg-[--border] flex-shrink-0 mt-2 overflow-hidden">
                  <div className="h-full bg-[--accent] rounded-full" style={{ width: `${entry.importance_score * 100}%` }} />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
