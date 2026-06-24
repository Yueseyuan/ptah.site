"use client";

import { useEffect, useState } from "react";
import { schedulerApi, ScheduledTask, ScheduleIn } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Calendar, Clock, Play, Pause, Trash2, Plus, X, Loader2,
  CheckCircle2, XCircle, Crown, AlertCircle,
} from "lucide-react";

const DAY_OPTIONS = [
  { value: "mon", label: "Monday" },
  { value: "tue", label: "Tuesday" },
  { value: "wed", label: "Wednesday" },
  { value: "thu", label: "Thursday" },
  { value: "fri", label: "Friday" },
  { value: "sat", label: "Saturday" },
  { value: "sun", label: "Sunday" },
];

function scheduleLabel(schedule: Record<string, unknown>): string {
  const type = schedule.type as string;
  if (type === "daily") return `Daily at ${String(schedule.hour ?? 9).padStart(2, "0")}:${String(schedule.minute ?? 0).padStart(2, "0")}`;
  if (type === "weekly") return `Every ${schedule.day ?? "mon"} at ${String(schedule.hour ?? 9).padStart(2, "0")}:${String(schedule.minute ?? 0).padStart(2, "0")}`;
  if (type === "interval") return `Every ${schedule.hours ?? 1}h${schedule.minutes ? ` ${schedule.minutes}m` : ""}`;
  if (type === "cron") return `Cron: ${schedule.expr}`;
  return "Unknown schedule";
}

function nextRunLabel(dt: string | null): string {
  if (!dt) return "Not scheduled";
  const d = new Date(dt);
  const diff = d.getTime() - Date.now();
  if (diff < 60_000) return "< 1 min";
  if (diff < 3_600_000) return `in ${Math.floor(diff / 60_000)}m`;
  if (diff < 86_400_000) return `in ${Math.floor(diff / 3_600_000)}h`;
  return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

interface FormState {
  name: string;
  goal: string;
  scheduleType: "daily" | "weekly" | "interval" | "cron";
  hour: string;
  minute: string;
  day: string;
  intervalHours: string;
  intervalMinutes: string;
  cronExpr: string;
}

const DEFAULT_FORM: FormState = {
  name: "",
  goal: "",
  scheduleType: "daily",
  hour: "9",
  minute: "0",
  day: "mon",
  intervalHours: "1",
  intervalMinutes: "0",
  cronExpr: "0 9 * * 1-5",
};

function buildSchedule(form: FormState): ScheduleIn {
  if (form.scheduleType === "daily") {
    return { type: "daily", hour: parseInt(form.hour), minute: parseInt(form.minute) };
  }
  if (form.scheduleType === "weekly") {
    return { type: "weekly", day: form.day, hour: parseInt(form.hour), minute: parseInt(form.minute) };
  }
  if (form.scheduleType === "interval") {
    return { type: "interval", hours: parseInt(form.intervalHours), minutes: parseInt(form.intervalMinutes) };
  }
  return { type: "cron", expr: form.cronExpr };
}

function TaskRow({
  task,
  onToggle,
  onDelete,
  onRunNow,
  running,
}: {
  task: ScheduledTask;
  onToggle: () => void;
  onDelete: () => void;
  onRunNow: () => void;
  running: boolean;
}) {
  return (
    <div className="flex items-start gap-4 px-5 py-4 hover:bg-[--surface-2] transition-colors">
      {/* Status indicator */}
      <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${task.enabled ? "bg-green-400" : "bg-[--text-muted]"}`} />

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-[--text-primary]">{task.name}</span>
          {task.last_run_status === "completed" && <CheckCircle2 size={12} className="text-green-400" />}
          {task.last_run_status === "failed" && <XCircle size={12} className="text-red-400" />}
        </div>
        <p className="text-xs text-[--text-secondary] truncate mb-1.5">{task.goal}</p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1 text-[10px] text-[--text-muted]">
            <Clock size={10} />
            {scheduleLabel(task.schedule as Record<string, unknown>)}
          </div>
          {task.next_run_at && (
            <div className="flex items-center gap-1 text-[10px] text-[--accent]">
              <Calendar size={10} />
              Next: {nextRunLabel(task.next_run_at)}
            </div>
          )}
          <div className="text-[10px] text-[--text-muted]">
            Runs: {task.run_count} · Errors: {task.error_count}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <button
          onClick={onRunNow}
          disabled={running}
          className="p-1.5 rounded-lg text-[--text-muted] hover:text-green-400 hover:bg-green-400/10 transition-colors disabled:opacity-40"
          title="Run now"
        >
          {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
        </button>
        <button
          onClick={onToggle}
          className={`p-1.5 rounded-lg transition-colors ${
            task.enabled
              ? "text-[--text-muted] hover:text-amber-400 hover:bg-amber-400/10"
              : "text-[--text-muted] hover:text-green-400 hover:bg-green-400/10"
          }`}
          title={task.enabled ? "Pause" : "Resume"}
        >
          {task.enabled ? <Pause size={13} /> : <Play size={13} />}
        </button>
        <button
          onClick={onDelete}
          className="p-1.5 rounded-lg text-[--text-muted] hover:text-red-400 hover:bg-red-400/10 transition-colors"
          title="Delete"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

export default function SchedulerPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [saving, setSaving] = useState(false);
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setTasks(await schedulerApi.list());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (!form.name.trim() || !form.goal.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await schedulerApi.create({ name: form.name, goal: form.goal, schedule: buildSchedule(form) });
      setForm(DEFAULT_FORM);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create task");
    } finally {
      setSaving(false);
    }
  }

  async function toggleTask(task: ScheduledTask) {
    try {
      await schedulerApi.update(task.id, { enabled: !task.enabled });
      await load();
    } catch {
      // ignore
    }
  }

  async function deleteTask(id: number) {
    try {
      await schedulerApi.delete(id);
      await load();
    } catch {
      // ignore
    }
  }

  async function runNow(id: number) {
    setRunningIds((s) => new Set([...s, id]));
    try {
      await schedulerApi.runNow(id);
    } catch {
      // ignore
    } finally {
      setRunningIds((s) => { const n = new Set(s); n.delete(id); return n; });
    }
  }

  const f = (k: keyof FormState, v: string) => setForm((p) => ({ ...p, [k]: v }));

  return (
    <div className="p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[--accent]/15 border border-[--accent]/25 flex items-center justify-center">
            <Calendar size={18} className="text-[--accent]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[--text-primary]">Scheduler</h1>
            <p className="text-sm text-[--text-secondary]">Run Chief goals automatically on a schedule</p>
          </div>
        </div>
        <Button onClick={() => setShowForm(true)} disabled={showForm}>
          <Plus size={14} />
          New Task
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-[--text-primary]">New Scheduled Task</h2>
            <button onClick={() => { setShowForm(false); setError(null); }} className="text-[--text-muted] hover:text-[--text-primary]">
              <X size={14} />
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <AlertCircle size={13} className="text-red-400" />
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-[--text-secondary] mb-1">Task Name</label>
              <input
                value={form.name}
                onChange={(e) => f("name", e.target.value)}
                placeholder="Daily marketing report"
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[--text-secondary] mb-1">
                Goal <span className="text-[--text-muted]">(what Chief should do)</span>
              </label>
              <textarea
                value={form.goal}
                onChange={(e) => f("goal", e.target.value)}
                placeholder="Research trending topics in AI, write 3 social media posts for Twitter and LinkedIn, and send a summary email to me@example.com"
                rows={3}
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] resize-none focus:outline-none focus:border-[--accent]/50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[--text-secondary] mb-2">Schedule</label>
              <div className="flex gap-2 mb-3">
                {(["daily", "weekly", "interval", "cron"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => f("scheduleType", t)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      form.scheduleType === t
                        ? "bg-[--accent] text-white"
                        : "bg-[--surface-2] text-[--text-secondary] hover:text-[--text-primary] border border-[--border]"
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>

              {(form.scheduleType === "daily" || form.scheduleType === "weekly") && (
                <div className="flex items-center gap-2">
                  {form.scheduleType === "weekly" && (
                    <select
                      value={form.day}
                      onChange={(e) => f("day", e.target.value)}
                      className="bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                    >
                      {DAY_OPTIONS.map((d) => (
                        <option key={d.value} value={d.value}>{d.label}</option>
                      ))}
                    </select>
                  )}
                  <input
                    type="number" min={0} max={23} value={form.hour}
                    onChange={(e) => f("hour", e.target.value)}
                    className="w-20 bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                  />
                  <span className="text-[--text-muted] text-sm">:</span>
                  <input
                    type="number" min={0} max={59} value={form.minute}
                    onChange={(e) => f("minute", e.target.value)}
                    className="w-20 bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                  />
                  <span className="text-xs text-[--text-muted]">UTC</span>
                </div>
              )}

              {form.scheduleType === "interval" && (
                <div className="flex items-center gap-2">
                  <input
                    type="number" min={0} value={form.intervalHours}
                    onChange={(e) => f("intervalHours", e.target.value)}
                    className="w-20 bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                  />
                  <span className="text-xs text-[--text-muted]">hours</span>
                  <input
                    type="number" min={0} max={59} value={form.intervalMinutes}
                    onChange={(e) => f("intervalMinutes", e.target.value)}
                    className="w-20 bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                  />
                  <span className="text-xs text-[--text-muted]">minutes</span>
                </div>
              )}

              {form.scheduleType === "cron" && (
                <input
                  value={form.cronExpr}
                  onChange={(e) => f("cronExpr", e.target.value)}
                  placeholder="0 9 * * 1-5"
                  className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm font-mono text-[--text-primary] focus:outline-none focus:border-[--accent]/50"
                />
              )}
            </div>

            <div className="flex gap-2 pt-1">
              <Button onClick={create} loading={saving} disabled={!form.name.trim() || !form.goal.trim()}>
                <Crown size={13} />
                Create Task
              </Button>
              <Button variant="secondary" onClick={() => { setShowForm(false); setError(null); }}>
                Cancel
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Task list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-[--surface] border border-[--border] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <Card className="text-center py-16 border-dashed">
          <Calendar size={40} className="text-[--text-muted] mx-auto mb-4 opacity-40" />
          <p className="text-base font-medium text-[--text-secondary] mb-2">No scheduled tasks</p>
          <p className="text-sm text-[--text-muted] max-w-sm mx-auto leading-relaxed">
            Schedule Chief to send emails, post to social media, research competitors,
            or run any goal automatically on your chosen schedule.
          </p>
          <Button className="mt-5" onClick={() => setShowForm(true)}>
            <Plus size={14} />
            Create your first task
          </Button>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-[--border] flex items-center justify-between">
            <span className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide">
              {tasks.length} task{tasks.length !== 1 ? "s" : ""}
            </span>
            <div className="flex items-center gap-2">
              <Badge variant="success">{tasks.filter((t) => t.enabled).length} active</Badge>
              {tasks.filter((t) => !t.enabled).length > 0 && (
                <Badge variant="secondary">{tasks.filter((t) => !t.enabled).length} paused</Badge>
              )}
            </div>
          </div>
          <div className="divide-y divide-[--border]">
            {tasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                onToggle={() => toggleTask(task)}
                onDelete={() => deleteTask(task.id)}
                onRunNow={() => runNow(task.id)}
                running={runningIds.has(task.id)}
              />
            ))}
          </div>
        </Card>
      )}

      {/* Info cards */}
      <div className="mt-8 grid grid-cols-2 gap-4">
        {[
          {
            title: "Email Campaigns",
            desc: "\"Write and send a weekly newsletter about AI trends to subscriber@email.com\"",
            color: "text-blue-400",
          },
          {
            title: "Social Media",
            desc: "\"Write 3 posts about our product updates and post to Twitter and LinkedIn\"",
            color: "text-purple-400",
          },
          {
            title: "Competitor Research",
            desc: "\"Fetch competitor.com, analyze their pricing page, write a comparison report\"",
            color: "text-amber-400",
          },
          {
            title: "Daily Reports",
            desc: "\"Research today's AI news, summarize the top 5 stories, email to me@example.com\"",
            color: "text-green-400",
          },
        ].map((card) => (
          <div
            key={card.title}
            className="p-4 rounded-xl bg-[--surface] border border-[--border] cursor-pointer hover:border-[--accent]/30 transition-colors"
            onClick={() => {
              setForm({ ...DEFAULT_FORM, name: card.title, goal: card.desc.replace(/"/g, "") });
              setShowForm(true);
            }}
          >
            <p className={`text-xs font-semibold mb-1 ${card.color}`}>{card.title}</p>
            <p className="text-[10px] text-[--text-muted] leading-relaxed italic">{card.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
