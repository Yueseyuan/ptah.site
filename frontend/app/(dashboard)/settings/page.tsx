"use client";

import { useEffect, useState } from "react";
import { modelsApi, Provider, ModelInfo } from "@/lib/api";
import { isTauri, tauriBackend, tauriDatabase, DatabaseInfo } from "@/lib/tauri";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Cpu, Layers, Monitor, Database, Play, Square, Download, Upload } from "lucide-react";

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
                <span className="text-xs text-[--text-muted]">{m.context_length.toLocaleString()} ctx</span>
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
