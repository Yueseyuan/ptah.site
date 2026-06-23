"use client";

import { useEffect, useState } from "react";
import { agentsApi, memoryApi, workflowsApi, reviewsApi, modelsApi, Provider } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Bot, Brain, GitBranch, Star, Cpu } from "lucide-react";

interface Stat {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stat[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [agents, entries, workflows, reviews, providerList] = await Promise.allSettled([
          agentsApi.list(),
          memoryApi.listEntries(),
          workflowsApi.list(),
          reviewsApi.list(),
          modelsApi.listProviders(),
        ]);

        setStats([
          {
            label: "Agents",
            value: agents.status === "fulfilled" ? agents.value.length : "—",
            icon: Bot,
            color: "text-violet-400",
          },
          {
            label: "Memory Entries",
            value: entries.status === "fulfilled" ? entries.value.length : "—",
            icon: Brain,
            color: "text-blue-400",
          },
          {
            label: "Workflows",
            value: workflows.status === "fulfilled" ? workflows.value.length : "—",
            icon: GitBranch,
            color: "text-green-400",
          },
          {
            label: "Repo Reviews",
            value: reviews.status === "fulfilled" ? reviews.value.length : "—",
            icon: Star,
            color: "text-amber-400",
          },
        ]);

        if (providerList.status === "fulfilled") {
          setProviders(providerList.value);
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[--text-primary]">Dashboard</h1>
        <p className="text-sm text-[--text-secondary] mt-1">APEX AI local intelligence overview</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-8 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-[--surface] border border-[--border] rounded-xl p-5 animate-pulse h-24" />
            ))
          : stats.map((s) => (
              <Card key={s.label}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-[--text-muted] mb-1">{s.label}</p>
                    <p className="text-2xl font-bold text-[--text-primary]">{s.value}</p>
                  </div>
                  <s.icon size={18} className={s.color} />
                </div>
              </Card>
            ))}
      </div>

      {/* Model Providers */}
      <div>
        <h2 className="text-sm font-semibold text-[--text-secondary] mb-3 uppercase tracking-wide">Model Providers</h2>
        {loading ? (
          <div className="bg-[--surface] border border-[--border] rounded-xl p-5 animate-pulse h-20" />
        ) : providers.length === 0 ? (
          <Card>
            <div className="flex items-center gap-3">
              <Cpu size={16} className="text-[--text-muted]" />
              <p className="text-sm text-[--text-secondary]">No model providers configured. Add one in Settings.</p>
            </div>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {providers.map((p) => (
              <Card key={p.name}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-2 h-2 rounded-full ${p.healthy ? "bg-green-400" : "bg-red-400"}`} />
                    <span className="text-sm font-medium text-[--text-primary]">{p.name}</span>
                  </div>
                  <span className="text-xs text-[--text-muted]">{p.model_count} models</span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
