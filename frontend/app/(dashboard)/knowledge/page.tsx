"use client";

import { useEffect, useState } from "react";
import { knowledgeApi, KnowledgeNode } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Network, Search, X } from "lucide-react";

const NODE_TYPES = ["concept", "entity", "fact", "procedure", "principle", "relationship"] as const;

const nodeTypeColors: Record<string, Parameters<typeof Badge>[0]["variant"]> = {
  concept: "purple",
  entity: "info",
  fact: "success",
  procedure: "warn",
  principle: "default",
  relationship: "danger",
};

export default function KnowledgePage() {
  const [nodes, setNodes] = useState<KnowledgeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [nodeType, setNodeType] = useState("concept");
  const [content, setContent] = useState("");
  const [confidence, setConfidence] = useState("1.0");
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      const data = typeFilter
        ? await knowledgeApi.listNodes(typeFilter)
        : await knowledgeApi.listNodes();
      setNodes(data);
    } finally {
      setLoading(false);
    }
  }

  async function search() {
    if (!q.trim()) return load();
    setLoading(true);
    try {
      setNodes(await knowledgeApi.search(q.trim()));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [typeFilter]);

  async function create() {
    if (!title.trim()) return;
    setCreating(true);
    try {
      await knowledgeApi.createNode({
        title: title.trim(),
        node_type: nodeType,
        content: content.trim() || undefined,
        confidence_score: parseFloat(confidence) || 1.0,
      });
      setTitle(""); setContent(""); setShowCreate(false);
      load();
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">Knowledge Graph</h1>
          <p className="text-sm text-[--text-secondary] mt-0.5">{nodes.length} nodes</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New Node
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {["", ...NODE_TYPES].map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${typeFilter === t ? "bg-[--accent] text-white" : "bg-[--surface] border border-[--border] text-[--text-secondary] hover:text-[--text-primary]"}`}
          >
            {t || "All"}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-6">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search nodes..." className="flex-1" onKeyDown={(e) => e.key === "Enter" && search()} />
        <Button variant="secondary" onClick={search}><Search size={14} /></Button>
        {q && <Button variant="ghost" onClick={() => { setQ(""); load(); }}><X size={14} /></Button>}
      </div>

      {/* Create form */}
      {showCreate && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[--text-primary]">New Knowledge Node</h3>
            <button onClick={() => setShowCreate(false)} className="text-[--text-muted] hover:text-[--text-primary]"><X size={14} /></button>
          </div>
          <div className="space-y-3">
            <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Node title" />
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-[--text-secondary]">Type</label>
                <select value={nodeType} onChange={(e) => setNodeType(e.target.value)} className="bg-[--surface-2] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]">
                  {NODE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <Input label="Confidence (0–1)" value={confidence} onChange={(e) => setConfidence(e.target.value)} type="number" min="0" max="1" step="0.05" />
            </div>
            <Textarea label="Content" value={content} onChange={(e) => setContent(e.target.value)} rows={3} placeholder="Describe this node..." />
            <div className="flex gap-2">
              <Button onClick={create} loading={creating} size="sm">Create</Button>
              <Button variant="ghost" onClick={() => setShowCreate(false)} size="sm">Cancel</Button>
            </div>
          </div>
        </Card>
      )}

      {/* Nodes */}
      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="bg-[--surface] border border-[--border] rounded-xl h-20 animate-pulse"/>)}</div>
      ) : nodes.length === 0 ? (
        <Card className="text-center py-12">
          <Network size={32} className="text-[--text-muted] mx-auto mb-3" />
          <p className="text-sm text-[--text-secondary]">No knowledge nodes yet.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {nodes.map((node) => (
            <Card key={node.id}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium text-[--text-primary]">{node.title}</p>
                    <Badge variant={nodeTypeColors[node.node_type] ?? "default"}>{node.node_type}</Badge>
                  </div>
                  {node.content && <p className="text-xs text-[--text-secondary] line-clamp-2">{node.content}</p>}
                  <p className="text-[10px] text-[--text-muted] mt-1.5">Confidence: {(node.confidence_score * 100).toFixed(0)}%</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="w-8 h-8 rounded-full border-2 border-[--border] flex items-center justify-center" style={{ borderColor: `hsl(${node.confidence_score * 120}, 60%, 50%)` }}>
                    <span className="text-[10px] font-bold text-[--text-secondary]">{(node.confidence_score * 100).toFixed(0)}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
