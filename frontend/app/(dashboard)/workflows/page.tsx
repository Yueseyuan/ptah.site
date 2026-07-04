"use client";

import { useEffect, useState } from "react";
import { workflowsApi, Workflow, WorkflowStep } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge, statusBadgeVariant } from "@/components/ui/badge";
import { Plus, GitBranch, Play, ChevronRight, X } from "lucide-react";

const STEP_TYPES = ["agent", "skill", "tool", "prompt", "condition", "parallel", "human"] as const;

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newStepName, setNewStepName] = useState("");
  const [newStepType, setNewStepType] = useState("agent");
  const [addingStep, setAddingStep] = useState(false);
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState<string | null>(null);

  async function load() {
    try {
      setWorkflows(await workflowsApi.list());
    } finally {
      setLoading(false);
    }
  }

  async function selectWorkflow(wf: Workflow) {
    setSelected(wf);
    setRunMsg(null);
    setSteps(await workflowsApi.listSteps(wf.id));
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await workflowsApi.create({ name: name.trim() });
      setName(""); setShowCreate(false);
      load();
    } finally {
      setCreating(false);
    }
  }

  async function addStep() {
    if (!selected || !newStepName.trim()) return;
    setAddingStep(true);
    try {
      await workflowsApi.addStep(selected.id, { name: newStepName.trim(), step_type: newStepType, order_index: steps.length });
      setNewStepName("");
      setSteps(await workflowsApi.listSteps(selected.id));
    } finally {
      setAddingStep(false);
    }
  }

  async function runWorkflow() {
    if (!selected) return;
    setRunning(true); setRunMsg(null);
    try {
      const run = await workflowsApi.createRun(selected.id);
      setRunMsg(`Run #${run.id} started with status: ${run.status}`);
    } catch (e: unknown) {
      setRunMsg(`Error: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setRunning(false);
    }
  }

  const activate = async (wf: Workflow) => {
    await workflowsApi.update(wf.id, { status: wf.status === "active" ? "draft" : "active" });
    load();
    if (selected?.id === wf.id) selectWorkflow({ ...wf, status: wf.status === "active" ? "draft" : "active" });
  };

  return (
    <div className="p-8 flex gap-6 h-[calc(100vh-0px)] overflow-hidden">
      {/* Left panel */}
      <div className="w-72 flex-shrink-0 flex flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-[--text-primary]">Workflows</h1>
          <Button size="sm" onClick={() => setShowCreate(true)}><Plus size={13} /></Button>
        </div>

        {showCreate && (
          <Card>
            <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Workflow name" />
            <div className="flex gap-2 mt-3">
              <Button size="sm" onClick={create} loading={creating}>Create</Button>
              <Button size="sm" variant="ghost" onClick={() => setShowCreate(false)}><X size={13} /></Button>
            </div>
          </Card>
        )}

        {loading ? (
          <div className="space-y-2">{[1,2,3].map(i=><div key={i} className="h-16 bg-[--surface] border border-[--border] rounded-xl animate-pulse"/>)}</div>
        ) : workflows.length === 0 ? (
          <Card className="text-center py-8">
            <GitBranch size={24} className="text-[--text-muted] mx-auto mb-2" />
            <p className="text-xs text-[--text-secondary]">No workflows yet</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {workflows.map((wf) => (
              <Card key={wf.id} onClick={() => selectWorkflow(wf)} className={selected?.id === wf.id ? "border-[--accent]/50" : ""}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[--text-primary] truncate">{wf.name}</p>
                    <Badge variant={statusBadgeVariant(wf.status)}>{wf.status}</Badge>
                  </div>
                  <ChevronRight size={14} className="text-[--text-muted] mt-0.5 flex-shrink-0" />
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto">
        {!selected ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <GitBranch size={40} className="text-[--text-muted] mx-auto mb-3" />
              <p className="text-sm text-[--text-secondary]">Select a workflow to view steps</p>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-[--text-primary]">{selected.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={statusBadgeVariant(selected.status)}>{selected.status}</Badge>
                  <span className="text-xs text-[--text-muted]">{steps.length} steps</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => activate(selected)}>
                  {selected.status === "active" ? "Deactivate" : "Activate"}
                </Button>
                <Button size="sm" onClick={runWorkflow} loading={running}>
                  <Play size={12} /> Run
                </Button>
              </div>
            </div>

            {runMsg && (
              <div className="mb-4 bg-[--surface] border border-[--border] rounded-lg px-4 py-2.5 text-sm text-[--text-secondary]">
                {runMsg}
              </div>
            )}

            {/* Steps */}
            <div className="space-y-2 mb-6">
              {steps.map((step, idx) => (
                <div key={step.id} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-[--accent-muted] text-[--accent] text-xs font-bold flex items-center justify-center flex-shrink-0">
                    {idx + 1}
                  </div>
                  <Card className="flex-1 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[--text-primary]">{step.name}</span>
                      <Badge variant="default">{step.step_type}</Badge>
                    </div>
                  </Card>
                </div>
              ))}
            </div>

            {/* Add step */}
            <Card>
              <p className="text-xs font-medium text-[--text-secondary] mb-3">Add Step</p>
              <div className="flex gap-2">
                <Input value={newStepName} onChange={(e) => setNewStepName(e.target.value)} placeholder="Step name" className="flex-1" />
                <select value={newStepType} onChange={(e) => setNewStepType(e.target.value)} className="bg-[--surface-2] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]">
                  {STEP_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <Button size="md" onClick={addStep} loading={addingStep}><Plus size={14} /></Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
