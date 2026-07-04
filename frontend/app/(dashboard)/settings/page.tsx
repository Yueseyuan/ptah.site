"use client";

import { useEffect, useState } from "react";
import { modelsApi, claritasApi, mediaApi, agencyApi, skillsShApi, ClaritasStatus, ClaritasSeedResult, MediaStatus, MediaSeedResult, AgencyStatus, AgencySeedResult, SkillCatalogEntry, Provider, ModelInfo } from "@/lib/api";
import { isTauri, tauriBackend, tauriDatabase, DatabaseInfo } from "@/lib/tauri";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Cpu, Layers, Monitor, Database, Play, Square, Download, Upload, Crown, Code, Search, Zap, Terminal, WifiOff, Image, Music, Video, Box, Sparkles, Users, BookOpen, Check, X } from "lucide-react";

const MEDIA_AGENT_ICONS: Record<string, React.ReactNode> = {
  "Image Creator": <Image size={13} />,
  "Audio Producer": <Music size={13} />,
  "Video Creator": <Video size={13} />,
  "3D Modeler": <Box size={13} />,
  "Image Enhancer": <Sparkles size={13} />,
};

function MediaAgentsPanel() {
  const [status, setStatus] = useState<MediaStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [result, setResult] = useState<MediaSeedResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    try {
      const s = await mediaApi.status();
      setStatus(s);
    } catch {
      // backend may not be running yet
    }
  }

  useEffect(() => { loadStatus(); }, []);

  async function handleSeed() {
    setSeeding(true);
    setError(null);
    setResult(null);
    try {
      const r = await mediaApi.seed();
      setResult(r);
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  const allInstalled = status != null && status.installed >= status.available;

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <Image size={13} /> Media Generation Agents
      </h2>

      <Card>
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <p className="text-sm font-medium text-[--text-primary] mb-1">HuggingFace Media Suite</p>
            <p className="text-xs text-[--text-secondary] leading-relaxed">
              5 pre-built agents for image, audio, video, and 3D generation — all free via HuggingFace Inference API.
              Requires <code className="bg-[--surface-2] px-1 rounded">HUGGINGFACE_API_TOKEN</code> in your backend <code className="bg-[--surface-2] px-1 rounded">.env</code>.
            </p>
          </div>
          {status != null && (
            <Badge variant={allInstalled ? "success" : "default"} className="ml-4 shrink-0">
              {status.installed} / {status.available} installed
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-1.5 mb-4">
          {Object.entries(MEDIA_AGENT_ICONS).map(([name, icon]) => (
            <div key={name} className="flex items-center gap-1.5 text-xs text-[--text-muted]">
              <span className="text-[--text-muted]">{icon}</span>
              {name}
            </div>
          ))}
        </div>

        {!allInstalled && (
          <Button size="sm" onClick={handleSeed} loading={seeding} disabled={seeding}>
            Install Media Agents
          </Button>
        )}

        {result != null && (
          <div className="mt-3">
            {result.skipped === 5 ? (
              <p className="text-xs text-[--text-secondary]">All media agents already installed.</p>
            ) : (
              <div>
                <p className="text-xs text-[--text-secondary] mb-2">
                  Installed {result.seeded} agent{result.seeded !== 1 ? "s" : ""}
                  {result.skipped > 0 ? `, skipped ${result.skipped} already present` : ""}.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.agents.map((name) => (
                    <Badge key={name} variant="success" className="text-[10px]">{name}</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {error != null && <p className="mt-2 text-xs text-red-400">{error}</p>}
        {allInstalled && result == null && (
          <p className="text-xs text-[--text-secondary]">All media agents installed.</p>
        )}
      </Card>
    </section>
  );
}

const SKILL_CATEGORY_COLORS: Record<string, string> = {
  python: "text-yellow-400",
  typescript: "text-blue-400",
  react: "text-cyan-400",
  database: "text-green-400",
  tools: "text-purple-400",
  architecture: "text-orange-400",
  security: "text-red-400",
  testing: "text-pink-400",
  go: "text-teal-400",
  rust: "text-amber-400",
};

function SkillsShPanel() {
  const [catalog, setCatalog] = useState<SkillCatalogEntry[]>([]);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ slug: string; ok: boolean; chars?: number } | null>(null);

  useEffect(() => {
    skillsShApi.catalog().then(setCatalog).catch(() => {});
  }, []);

  async function handleTest(slug: string) {
    setTesting(slug);
    setTestResult(null);
    try {
      const r = await skillsShApi.fetch(slug);
      setTestResult({ slug, ok: true, chars: r.length });
    } catch {
      setTestResult({ slug, ok: false });
    } finally {
      setTesting(null);
    }
  }

  const byCategory = catalog.reduce<Record<string, SkillCatalogEntry[]>>((acc, s) => {
    (acc[s.category] ??= []).push(s);
    return acc;
  }, {});

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <BookOpen size={13} /> skills.sh — Agent Skill Modules
      </h2>

      <Card>
        <p className="text-sm font-medium text-[--text-primary] mb-1">skills.sh Integration</p>
        <p className="text-xs text-[--text-secondary] leading-relaxed mb-4">
          Skill modules are SKILL.md files fetched from the{" "}
          <code className="bg-[--surface-2] px-1 rounded">skills.sh</code> public registry and injected
          into an agent&apos;s system prompt at run time. Add a{" "}
          <code className="bg-[--surface-2] px-1 rounded">skills</code> array to an agent&apos;s version
          config to activate them.
        </p>

        <div className="border border-[--border] rounded-lg p-3 mb-4">
          <p className="text-[10px] font-medium text-[--text-primary] mb-2">Agent version config example</p>
          <pre className="text-[10px] text-[--text-muted] font-mono leading-relaxed">{`{
  "division": "engineering",
  "skills": ["python-patterns", "fastapi-patterns"]
}`}</pre>
        </div>

        {Object.entries(byCategory).map(([cat, skills]) => (
          <div key={cat} className="mb-4">
            <p className={`text-[10px] font-semibold uppercase tracking-wide mb-1.5 ${SKILL_CATEGORY_COLORS[cat] ?? "text-[--text-muted]"}`}>
              {cat}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {skills.map((s) => (
                <button
                  key={s.slug}
                  onClick={() => handleTest(s.slug)}
                  disabled={testing === s.slug}
                  className="flex items-center gap-1 text-[10px] text-[--text-secondary] bg-[--surface-2] hover:bg-[--surface] border border-[--border] px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                >
                  {testing === s.slug ? (
                    <span className="w-2.5 h-2.5 border border-current border-t-transparent rounded-full animate-spin inline-block" />
                  ) : testResult?.slug === s.slug ? (
                    testResult.ok
                      ? <Check size={10} className="text-green-400" />
                      : <X size={10} className="text-red-400" />
                  ) : null}
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        ))}

        {testResult && (
          <p className={`text-xs mt-2 ${testResult.ok ? "text-green-400" : "text-red-400"}`}>
            {testResult.ok
              ? `✓ ${testResult.slug} fetched (${testResult.chars?.toLocaleString()} chars)`
              : `✗ Could not fetch ${testResult.slug} — check network or slug`}
          </p>
        )}
      </Card>
    </section>
  );
}

const AGENCY_DIVISIONS = [
  "Engineering", "Design", "Marketing", "Sales", "Product", "Project Management",
  "Testing", "Security", "Support", "Finance", "Specialized", "Game Development",
  "Academic", "GIS", "Paid Media", "Spatial Computing",
];

function AgencyPanel() {
  const [status, setStatus] = useState<AgencyStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [result, setResult] = useState<AgencySeedResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    try {
      const s = await agencyApi.status();
      setStatus(s);
    } catch {
      // backend may not be running yet
    }
  }

  useEffect(() => { loadStatus(); }, []);

  async function handleSeed() {
    setSeeding(true);
    setError(null);
    setResult(null);
    try {
      const r = await agencyApi.seed();
      setResult(r);
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  const allInstalled = status != null && status.installed >= status.available;

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <Users size={13} /> The Agency — 232 Specialists
      </h2>

      <Card>
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <p className="text-sm font-medium text-[--text-primary] mb-1">Agency Specialist Agents</p>
            <p className="text-xs text-[--text-secondary] leading-relaxed">
              232 specialist AI agents spanning 16 divisions — engineering, design, security, finance, and more.
              All run locally via Ollama. Sourced from the open-source <code className="bg-[--surface-2] px-1 rounded">agency-agents</code> library.
            </p>
          </div>
          {status != null && (
            <Badge variant={allInstalled ? "success" : "default"} className="ml-4 shrink-0">
              {status.installed} / {status.available}
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap gap-1 mb-4">
          {AGENCY_DIVISIONS.map((div) => (
            <span key={div} className="text-[10px] text-[--text-muted] bg-[--surface-2] px-1.5 py-0.5 rounded">
              {div}
            </span>
          ))}
        </div>

        {!allInstalled && (
          <Button size="sm" onClick={handleSeed} loading={seeding} disabled={seeding}>
            {seeding ? "Downloading agents…" : "Install 232 Agents"}
          </Button>
        )}

        {result != null && (
          <div className="mt-3">
            <p className="text-xs text-[--text-secondary]">
              Installed {result.seeded} agent{result.seeded !== 1 ? "s" : ""}
              {result.skipped > 0 ? `, skipped ${result.skipped} already present` : ""}.
              {result.total_found !== result.seeded + result.skipped
                ? ` (${result.total_found} found in source)`
                : ""}
            </p>
          </div>
        )}

        {error != null && <p className="mt-2 text-xs text-red-400">{error}</p>}
        {allInstalled && result == null && (
          <p className="text-xs text-[--text-secondary]">All 232 agents installed.</p>
        )}
      </Card>
    </section>
  );
}

const FCC_PORT = 8003;
const FCC_BASE = `http://localhost:${FCC_PORT}`;

function FreeCCPanel() {
  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <WifiOff size={13} /> Free AI Proxy
      </h2>

      <Card>
        <p className="text-sm font-medium text-[--text-primary] mb-1">free-claude-code proxy</p>
        <p className="text-xs text-[--text-secondary] leading-relaxed mb-4">
          Routes Anthropic API calls to free providers — Gemini, NVIDIA NIM, OpenRouter.
          Zero subscriptions, zero usage limits. Requires a free port (not 8082).
        </p>

        <div className="border border-[--border] rounded-lg p-3 space-y-1.5">
          <p className="text-xs font-medium text-[--text-primary] mb-2">Setup (Windows)</p>
          {[
            { step: "1", label: "Install", code: "irm https://github.com/Alishahryar1/free-claude-code/blob/main/scripts/install.ps1?raw=1 | iex" },
            { step: "2", label: "Start on free port", code: `fcc-server --port ${FCC_PORT}` },
            { step: "3", label: "Add to backend .env", code: `ANTHROPIC_BASE_URL=http://localhost:${FCC_PORT}` },
            { step: "4", label: "Restart backend", code: "uvicorn app.main:app --port 8085" },
          ].map(({ step, label, code }) => (
            <div key={step} className="flex items-start gap-2">
              <span className="text-[10px] font-bold text-[--text-muted] w-4 shrink-0 mt-0.5">{step}.</span>
              <div className="flex-1 min-w-0">
                <span className="text-[10px] text-[--text-muted] block mb-0.5">{label}</span>
                <code className="text-[10px] text-[--text-secondary] bg-[--surface-2] px-1.5 py-0.5 rounded block break-all">{code}</code>
              </div>
            </div>
          ))}
        </div>

        <p className="text-[10px] text-[--text-muted] mt-3 pt-3 border-t border-[--border]">
          Configure free providers at <code className="bg-[--surface-2] px-1 rounded">http://localhost:8082/admin</code> after starting.
        </p>
      </Card>
    </section>
  );
}

// Icons matched to each CL4R1T4S agent
const AGENT_ICONS: Record<string, React.ReactNode> = {
  "Devin": <Crown size={13} />,
  "Cursor": <Code size={13} />,
  "Perplexity Research": <Search size={13} />,
  "Manus": <Zap size={13} />,
  "v0 UI Builder": <Layers size={13} />,
  "Claude Code": <Terminal size={13} />,
};

function ClaritasPanel() {
  const [status, setStatus] = useState<ClaritasStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [result, setResult] = useState<ClaritasSeedResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    try {
      const s = await claritasApi.status();
      setStatus(s);
    } catch {
      // silently ignore — backend may not be running yet
    }
  }

  useEffect(() => { loadStatus(); }, []);

  async function handleSeed() {
    setSeeding(true);
    setError(null);
    setResult(null);
    try {
      const r = await claritasApi.seed();
      setResult(r);
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  const allInstalled = status != null && status.installed >= status.available;

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <Crown size={13} /> CL4R1T4S Agent Templates
      </h2>

      <Card>
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <p className="text-sm font-medium text-[--text-primary] mb-1">Pre-built AI Agents</p>
            <p className="text-xs text-[--text-secondary] leading-relaxed">
              Install 6 pre-built agents powered by system prompts from the CL4R1T4S library.
              These agents run locally via Ollama — no subscriptions or usage limits.
            </p>
          </div>
          {status != null && (
            <Badge variant={allInstalled ? "success" : "default"} className="ml-4 shrink-0">
              {status.installed} / {status.available} installed
            </Badge>
          )}
        </div>

        {/* Agent list */}
        <div className="grid grid-cols-2 gap-1.5 mb-4">
          {Object.entries(AGENT_ICONS).map(([name, icon]) => (
            <div key={name} className="flex items-center gap-1.5 text-xs text-[--text-muted]">
              <span className="text-[--text-muted]">{icon}</span>
              {name}
            </div>
          ))}
        </div>

        {/* Seed button */}
        {!allInstalled && (
          <Button size="sm" onClick={handleSeed} loading={seeding} disabled={seeding}>
            Install All Agents
          </Button>
        )}

        {/* Results */}
        {result != null && (
          <div className="mt-3">
            {result.skipped === 6 ? (
              <p className="text-xs text-[--text-secondary]">All templates already installed.</p>
            ) : (
              <div>
                <p className="text-xs text-[--text-secondary] mb-2">
                  Installed {result.seeded} agent{result.seeded !== 1 ? "s" : ""}
                  {result.skipped > 0 ? `, skipped ${result.skipped} already present` : ""}.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.agents.map((name) => (
                    <Badge key={name} variant="success" className="text-[10px]">
                      {name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {error != null && (
          <p className="mt-2 text-xs text-red-400">{error}</p>
        )}

        {allInstalled && result == null && (
          <p className="text-xs text-[--text-secondary]">All templates already installed.</p>
        )}
      </Card>
    </section>
  );
}

function DesktopPanel() {
  const [backendStatus, setBackendStatus] = useState<string>("checking…");
  const [dbInfo, setDbInfo] = useState<DatabaseInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    try {
      const [s, d] = await Promise.all([tauriBackend.status(), tauriDatabase.info()]);
      setBackendStatus(s);
      setDbInfo(d);
    } catch {
      setBackendStatus("error");
    }
  }

  useEffect(() => { refresh(); }, []);

  async function handleStart() {
    setBusy(true);
    try {
      await tauriBackend.start();
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      await tauriBackend.stop();
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    setBusy(true);
    try {
      const { save } = await import("@tauri-apps/plugin-dialog");
      const dest = await save({ defaultPath: "apex_backup.db", filters: [{ name: "SQLite", extensions: ["db"] }] });
      if (dest) {
        await tauriDatabase.export(dest);
        setMessage("Database exported successfully.");
      }
    } catch (e) {
      setMessage(`Export failed: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleImport() {
    setBusy(true);
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const src = await open({ filters: [{ name: "SQLite", extensions: ["db"] }] });
      if (src && typeof src === "string") {
        await tauriDatabase.import(src);
        setMessage("Database imported. Restart the backend for changes to take effect.");
      }
    } catch (e) {
      setMessage(`Import failed: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  const isRunning = backendStatus.startsWith("running");

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3 flex items-center gap-2">
        <Monitor size={13} /> Desktop App
      </h2>

      {/* Backend control */}
      <Card className="mb-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? "bg-green-400 shadow-[0_0_8px_#4ade80]" : "bg-[--text-muted]"}`} />
            <div>
              <p className="text-sm font-medium text-[--text-primary]">Backend Process</p>
              <p className="text-xs text-[--text-muted]">{backendStatus}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {!isRunning ? (
              <Button size="sm" onClick={handleStart} loading={busy}>
                <Play size={12} className="mr-1" /> Start
              </Button>
            ) : (
              <Button size="sm" variant="ghost" onClick={handleStop} loading={busy}>
                <Square size={12} className="mr-1" /> Stop
              </Button>
            )}
          </div>
        </div>
        <p className="text-xs text-[--text-secondary]">
          The FastAPI backend runs locally on <code className="bg-[--surface-2] px-1 rounded">127.0.0.1:8000</code>.
          It starts automatically when APEX AI launches.
        </p>
      </Card>

      {/* Database info + backup/restore */}
      <Card>
        <div className="flex items-center gap-2 mb-3">
          <Database size={14} className="text-[--text-muted]" />
          <p className="text-sm font-medium text-[--text-primary]">Local Database</p>
          {dbInfo && (
            <Badge variant="default" className="ml-auto">
              {dbInfo.size_mb.toFixed(2)} MB
            </Badge>
          )}
        </div>
        {dbInfo && (
          <p className="text-[10px] text-[--text-muted] font-mono mb-3 truncate">{dbInfo.path}</p>
        )}
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={handleExport} loading={busy}>
            <Download size={12} className="mr-1" /> Export Backup
          </Button>
          <Button size="sm" variant="ghost" onClick={handleImport} loading={busy}>
            <Upload size={12} className="mr-1" /> Restore Backup
          </Button>
        </div>
        {message && (
          <p className="text-xs text-[--text-secondary] mt-2">{message}</p>
        )}
      </Card>
    </section>
  );
}

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [desktop, setDesktop] = useState(false);

  useEffect(() => {
    setDesktop(isTauri());
    async function load() {
      try {
        const [p, m] = await Promise.allSettled([modelsApi.listProviders(), modelsApi.listModels()]);
        if (p.status === "fulfilled") setProviders(p.value);
        if (m.status === "fulfilled") setModels(m.value);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[--text-primary]">Settings</h1>
        <p className="text-sm text-[--text-secondary] mt-1">Model provider configuration</p>
      </div>

      <MediaAgentsPanel />

      <AgencyPanel />

      <SkillsShPanel />

      <FreeCCPanel />

      <ClaritasPanel />

      {desktop && <DesktopPanel />}

      <section className="mb-8">
        <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3">Model Providers</h2>
        {loading ? (
          <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-16 bg-[--surface] border border-[--border] rounded-xl animate-pulse"/>)}</div>
        ) : providers.length === 0 ? (
          <Card>
            <div className="flex items-center gap-3 py-2">
              <Cpu size={16} className="text-[--text-muted]" />
              <div>
                <p className="text-sm font-medium text-[--text-primary]">No providers configured</p>
                <p className="text-xs text-[--text-secondary]">
                  Add provider settings to your <code className="bg-[--surface-2] px-1 rounded text-[10px]">.env</code> file and restart the backend.
                </p>
              </div>
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            {providers.map((p) => (
              <Card key={p.name}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${p.healthy ? "bg-green-400 shadow-[0_0_8px_#4ade80]" : "bg-red-400"}`} />
                    <div>
                      <p className="text-sm font-medium text-[--text-primary]">{p.name}</p>
                      <p className="text-xs text-[--text-muted]">{p.healthy ? "healthy" : "unreachable"}</p>
                    </div>
                  </div>
                  <Badge variant={p.healthy ? "success" : "danger"}>{p.model_count} models</Badge>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3">Available Models</h2>
        {loading ? (
          <div className="h-32 bg-[--surface] border border-[--border] rounded-xl animate-pulse" />
        ) : models.length === 0 ? (
          <Card>
            <div className="flex items-center gap-3 py-2">
              <Layers size={16} className="text-[--text-muted]" />
              <p className="text-sm text-[--text-secondary]">No models available from healthy providers</p>
            </div>
          </Card>
        ) : (
          <div className="space-y-2">
            {models.map((m) => (
              <div key={`${m.provider}/${m.id}`} className="flex items-center justify-between px-4 py-2.5 bg-[--surface] border border-[--border] rounded-lg">
                <div>
                  <span className="text-sm font-medium text-[--text-primary]">{m.name}</span>
                  <span className="text-xs text-[--text-muted] ml-2">{m.provider}</span>
                </div>
                <span className="text-xs text-[--text-muted]">{(m.context_length ?? 0).toLocaleString()} ctx</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-[--text-muted] uppercase tracking-wide mb-3">Configuration</h2>
        <Card>
          <p className="text-xs text-[--text-secondary] mb-3">Configure providers via environment variables in <code className="bg-[--surface-2] px-1 rounded">.env</code>:</p>
          <pre className="text-[10px] text-[--text-muted] font-mono leading-relaxed">
{`# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# llama.cpp
LLAMA_CPP_BASE_URL=http://localhost:8080`}
          </pre>
        </Card>
      </section>
    </div>
  );
}
