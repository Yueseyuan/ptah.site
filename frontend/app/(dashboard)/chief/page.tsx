"use client";

import { useEffect, useRef, useState } from "react";
import { chiefApi, ChiefRunResult, ChiefRunSummary, ChiefSubtask } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge, statusBadgeVariant } from "@/components/ui/badge";
import { Crown, Bot, Loader2, ChevronRight, Clock, CheckCircle2, XCircle, AlertCircle, Paperclip, X } from "lucide-react";

type Phase = "idle" | "planning" | "assigning" | "executing" | "merging" | "done" | "error";

const phaseLabels: Record<Phase, string> = {
  idle: "",
  planning: "Planning subtasks...",
  assigning: "Assigning agents...",
  executing: "Executing in parallel...",
  merging: "Merging results...",
  done: "Complete",
  error: "Failed",
};

function PhaseIndicator({ phase }: { phase: Phase }) {
  const steps: Phase[] = ["planning", "assigning", "executing", "merging"];
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {steps.map((step, idx) => {
        const stepIdx = steps.indexOf(phase);
        const isDone = stepIdx > idx || phase === "done";
        const isActive = step === phase;
        const isPending = stepIdx < idx && phase !== "done";
        return (
          <div key={step} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
                isDone
                  ? "bg-green-500/15 text-green-400 border border-green-500/25"
                  : isActive
                  ? "bg-[--accent]/15 text-[--accent] border border-[--accent]/30 animate-pulse"
                  : isPending
                  ? "bg-[--surface-2] text-[--text-muted] border border-[--border]"
                  : "bg-[--surface-2] text-[--text-muted] border border-[--border]"
              }`}
            >
              {isDone ? (
                <CheckCircle2 size={11} />
              ) : isActive ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full bg-current opacity-40" />
              )}
              {phaseLabels[step]}
            </div>
            {idx < steps.length - 1 && (
              <ChevronRight size={12} className="text-[--text-muted] opacity-40" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function SubtaskCard({ subtask, idx }: { subtask: ChiefSubtask; idx: number }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute top-0 left-0 w-0.5 h-full bg-[--accent]/40 rounded-l-xl" />
      <div className="pl-3">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-[10px] font-mono text-[--text-muted] flex-shrink-0">#{idx + 1}</span>
            <h3 className="text-sm font-semibold text-[--text-primary] truncate">{subtask.title}</h3>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-[--surface-2] border border-[--border]">
              <Bot size={10} className="text-[--accent]" />
              <span className="text-[10px] text-[--text-secondary]">{subtask.agent_name}</span>
            </div>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-[--text-muted] hover:text-[--text-primary] transition-colors"
            >
              <ChevronRight
                size={14}
                className={`transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
              />
            </button>
          </div>
        </div>
        <p className="text-xs text-[--text-secondary] mb-2 leading-relaxed">{subtask.description}</p>
        {expanded && subtask.output && (
          <div className="mt-3 pt-3 border-t border-[--border]">
            <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-1.5 font-medium">Output</p>
            <p className="text-xs text-[--text-secondary] leading-relaxed whitespace-pre-wrap">{subtask.output}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

function HistoryItem({ run, onSelect }: { run: ChiefRunSummary; onSelect: () => void }) {
  const goal = run.input?.goal as string | undefined;
  const date = new Date(run.created_at);
  return (
    <button
      onClick={onSelect}
      className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-[--surface-2] transition-colors group"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-[--text-primary] line-clamp-2 leading-relaxed flex-1">{goal ?? run.name}</p>
        <Badge variant={statusBadgeVariant(run.status)} className="flex-shrink-0 mt-0.5">{run.status}</Badge>
      </div>
      <p className="text-[10px] text-[--text-muted] mt-1">
        {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </p>
    </button>
  );
}

export default function ChiefPage() {
  const [goal, setGoal] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<ChiefRunResult | null>(null);
  const [history, setHistory] = useState<ChiefRunSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<ChiefRunSummary | null>(null);
  const [attachedFile, setAttachedFile] = useState<{ name: string; content: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function readFile(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setAttachedFile({ name: file.name, content });
      if (!goal.trim()) setGoal(`Analyze the following file (${file.name}):\n\n${content}`);
      else setGoal((g) => `${g}\n\n--- Attached: ${file.name} ---\n${content}`);
    };
    reader.readAsText(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) readFile(file);
    e.target.value = "";
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) readFile(file);
  }

  async function loadHistory() {
    try {
      const runs = await chiefApi.listRuns();
      setHistory(runs);
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  async function execute() {
    if (!goal.trim() || phase !== "idle") return;
    setResult(null);
    setSelectedRun(null);

    // Animate through phases
    setPhase("planning");
    await new Promise((r) => setTimeout(r, 600));
    setPhase("assigning");
    await new Promise((r) => setTimeout(r, 500));
    setPhase("executing");

    try {
      const res = await chiefApi.run(goal.trim());
      setPhase("merging");
      await new Promise((r) => setTimeout(r, 400));
      setResult(res);
      setPhase(res.error && !res.merged_output ? "error" : "done");
      loadHistory();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setResult({ run_id: null, subtasks: [], merged_output: null, error: msg });
      setPhase("error");
    }
  }

  function reset() {
    setPhase("idle");
    setResult(null);
    setSelectedRun(null);
    setAttachedFile(null);
    setGoal("");
  }

  async function selectHistoryRun(run: ChiefRunSummary) {
    setSelectedRun(run);
    setResult(null);
    // Reconstruct result from stored output
    if (run.output) {
      const subtasks: ChiefSubtask[] = Array.isArray(run.output.subtasks)
        ? (run.output.subtasks as ChiefSubtask[])
        : [];
      setResult({
        run_id: run.id,
        subtasks,
        merged_output: (run.output.merged_output as string) ?? null,
        error: run.error,
      });
    }
    setPhase("done");
  }

  const isRunning = phase === "planning" || phase === "assigning" || phase === "executing" || phase === "merging";

  return (
    <div className="flex h-full">
      {/* History sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-[--border] flex flex-col h-full bg-[--surface]">
        <div className="px-4 py-4 border-b border-[--border]">
          <h2 className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide">Past Runs</h2>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
          {historyLoading ? (
            <div className="space-y-2 p-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-[--surface-2] rounded-lg animate-pulse" />
              ))}
            </div>
          ) : history.length === 0 ? (
            <p className="text-xs text-[--text-muted] px-3 py-4 text-center">No runs yet</p>
          ) : (
            history.map((run) => (
              <HistoryItem
                key={run.id}
                run={run}
                onSelect={() => selectHistoryRun(run)}
              />
            ))
          )}
        </div>
      </aside>

      {/* Main area */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-3xl">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-[--accent]/15 border border-[--accent]/25 flex items-center justify-center">
              <Crown size={18} className="text-[--accent]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[--text-primary]">Chief</h1>
              <p className="text-sm text-[--text-secondary]">Orchestrate any goal across your AI agents</p>
            </div>
          </div>

          {/* Goal input */}
          {!selectedRun && (
            <Card
              className={`mb-6 transition-colors ${isDragging ? "border-[--accent]/60 bg-[--accent]/5" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <label className="block text-xs font-medium text-[--text-secondary] mb-2">
                What should the Chief accomplish?
              </label>

              {/* Attached file pill */}
              {attachedFile && (
                <div className="flex items-center gap-1.5 mb-2 px-2 py-1 rounded-md bg-[--accent]/10 border border-[--accent]/20 w-fit">
                  <Paperclip size={10} className="text-[--accent]" />
                  <span className="text-[10px] text-[--accent] font-medium">{attachedFile.name}</span>
                  <button
                    onClick={() => setAttachedFile(null)}
                    className="text-[--accent]/60 hover:text-[--accent] ml-1"
                  >
                    <X size={10} />
                  </button>
                </div>
              )}

              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                disabled={isRunning}
                placeholder={isDragging ? "Drop file here…" : "e.g. Research the latest AI frameworks and write a comparison report with code examples…"}
                rows={4}
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
              />

              <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-2">
                  {phase === "done" || phase === "error" ? (
                    <Button variant="secondary" size="sm" onClick={reset}>
                      New Goal
                    </Button>
                  ) : (
                    <Button
                      onClick={execute}
                      loading={isRunning}
                      disabled={!goal.trim() || isRunning}
                    >
                      <Crown size={14} />
                      Execute
                    </Button>
                  )}

                  {/* File upload button */}
                  {!isRunning && phase === "idle" && (
                    <>
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".txt,.md,.json,.csv,.py,.ts,.tsx,.js,.jsx,.html,.css,.yaml,.yml,.xml,.log,.sh,.sql"
                        onChange={handleFileInput}
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-[--text-muted] hover:text-[--text-primary] hover:bg-[--surface-2] border border-[--border] transition-colors"
                        title="Attach a file"
                      >
                        <Paperclip size={12} />
                        Attach
                      </button>
                    </>
                  )}
                </div>

                {isRunning ? (
                  <p className="text-xs text-[--text-muted] animate-pulse">{phaseLabels[phase]}</p>
                ) : (
                  <p className="text-[10px] text-[--text-muted]">or drag & drop a file</p>
                )}
              </div>
            </Card>
          )}

          {/* Phase progress */}
          {isRunning && (
            <div className="mb-6">
              <PhaseIndicator phase={phase} />
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-6">
              {/* Error banner */}
              {result.error && !result.merged_output && (
                <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                  <XCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-red-300 mb-1">Execution failed</p>
                    <p className="text-xs text-red-400/80">{result.error}</p>
                  </div>
                </div>
              )}

              {/* Partial error warning */}
              {result.error && result.merged_output && (
                <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/8 border border-amber-500/20">
                  <AlertCircle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-400/80">{result.error}</p>
                </div>
              )}

              {/* Subtask cards */}
              {result.subtasks.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide">
                      Agent Subtasks
                    </h2>
                    <Badge variant="info">{result.subtasks.length} tasks</Badge>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-1">
                    {result.subtasks.map((subtask, idx) => (
                      <SubtaskCard key={idx} subtask={subtask} idx={idx} />
                    ))}
                  </div>
                </div>
              )}

              {/* Merged output */}
              {result.merged_output && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={14} className="text-green-400" />
                    <h2 className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide">
                      Chief&apos;s Synthesis
                    </h2>
                  </div>
                  <div className="bg-[--surface] border border-[--border] rounded-xl p-5 relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-[--accent]/0 via-[--accent]/60 to-[--accent]/0" />
                    <p className="text-sm text-[--text-secondary] leading-relaxed whitespace-pre-wrap">
                      {result.merged_output}
                    </p>
                    {result.run_id && (
                      <div className="mt-4 pt-3 border-t border-[--border] flex items-center gap-1.5">
                        <Clock size={10} className="text-[--text-muted]" />
                        <span className="text-[10px] text-[--text-muted]">Run #{result.run_id}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* New goal button after viewing history */}
              {selectedRun && (
                <Button variant="secondary" size="sm" onClick={reset}>
                  New Goal
                </Button>
              )}
            </div>
          )}

          {/* Empty state for history view */}
          {phase === "done" && !result && selectedRun && (
            <Card className="text-center py-12">
              <Crown size={32} className="text-[--text-muted] mx-auto mb-3" />
              <p className="text-sm text-[--text-secondary]">No output stored for this run.</p>
            </Card>
          )}

          {/* Initial empty state */}
          {phase === "idle" && !result && (
            <Card className="text-center py-16 border-dashed">
              <Crown size={40} className="text-[--text-muted] mx-auto mb-4 opacity-40" />
              <p className="text-base font-medium text-[--text-secondary] mb-2">Ready for your command</p>
              <p className="text-sm text-[--text-muted] max-w-xs mx-auto leading-relaxed">
                Give the Chief a goal and it will decompose it, assign your agents, and synthesize the results.
              </p>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
