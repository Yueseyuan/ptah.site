"use client";

import { useEffect, useState } from "react";
import { agentsApi, Agent } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Badge, statusBadgeVariant } from "@/components/ui/badge";
import { Plus, Bot, Play, X } from "lucide-react";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [runInput, setRunInput] = useState("{}");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  async function load() {
    try {
      setAgents(await agentsApi.list());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await agentsApi.create({ name: name.trim(), description: description.trim() || undefined });
      setName(""); setDescription(""); setShowCreate(false);
      load();
    } finally {
      setCreating(false);
    }
  }

  async function runAgent() {
    if (!selected) return;
    setRunning(true); setRunResult(null);
    try {
      const input = JSON.parse(runInput);
      const run = await agentsApi.createRun(selected.id, input);
      setRunResult(JSON.stringify(run, null, 2));
    } catch (e: unknown) {
      setRunResult(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">Agents</h1>
          <p className="text-sm text-[--text-secondary] mt-0.5">Manage and run AI agents</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New Agent
        </Button>
      </div>

      {/* Create form */}
      {showCreate && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[--text-primary]">New Agent</h3>
            <button onClick={() => setShowCreate(false)} className="text-[--text-muted] hover:text-[--text-primary]">
              <X size={14} />
            </button>
          </div>
          <div className="space-y-3">
            <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. ResearchAgent" />
            <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this agent do?" rows={2} />
            <div className="flex gap-2">
              <Button onClick={create} loading={creating} size="sm">Create</Button>
              <Button variant="ghost" onClick={() => setShowCreate(false)} size="sm">Cancel</Button>
            </div>
          </div>
        </Card>
      )}

      {/* Agent list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="bg-[--surface] border border-[--border] rounded-xl h-20 animate-pulse" />)}
        </div>
      ) : agents.length === 0 ? (
        <Card className="text-center py-12">
          <Bot size={32} className="text-[--text-muted] mx-auto mb-3" />
          <p className="text-sm text-[--text-secondary]">No agents yet. Create your first agent above.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {agents.map((agent) => (
            <Card key={agent.id} onClick={() => setSelected(agent === selected ? null : agent)}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[--accent-muted] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot size={14} className="text-[--accent]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[--text-primary]">{agent.name}</p>
                    {agent.description && <p className="text-xs text-[--text-secondary] mt-0.5">{agent.description}</p>}
                    <p className="text-[10px] text-[--text-muted] mt-1">ID: {agent.id} · Created {new Date(agent.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <Badge variant={statusBadgeVariant(agent.is_active ? "active" : "failed")}>
                  {agent.is_active ? "active" : "inactive"}
                </Badge>
              </div>

              {/* Run panel */}
              {selected?.id === agent.id && (
                <div className="mt-4 pt-4 border-t border-[--border]" onClick={(e) => e.stopPropagation()}>
                  <p className="text-xs font-medium text-[--text-secondary] mb-2">Run Input (JSON)</p>
                  <Textarea
                    value={runInput}
                    onChange={(e) => setRunInput(e.target.value)}
                    rows={3}
                    className="font-mono text-xs"
                  />
                  <div className="flex gap-2 mt-3">
                    <Button size="sm" onClick={runAgent} loading={running}>
                      <Play size={12} /> Run
                    </Button>
                  </div>
                  {runResult && (
                    <pre className="mt-3 bg-[--bg] border border-[--border] rounded-lg p-3 text-xs text-[--text-secondary] overflow-auto max-h-48">
                      {runResult}
                    </pre>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
