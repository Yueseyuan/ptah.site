"use client";

import { useEffect, useState } from "react";
import { modelsApi, Provider, ModelInfo } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Cpu, Layers } from "lucide-react";

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

      {/* Environment hints */}
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
