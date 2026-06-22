"use client";

import { useEffect, useState } from "react";
import { reviewsApi, RepoReview, ReviewStage } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge, statusBadgeVariant } from "@/components/ui/badge";
import { Plus, Star, CheckCircle, AlertTriangle, XCircle, MinusCircle, X } from "lucide-react";

const CLASSIFICATION_LABELS: Record<string, string> = {
  use_directly: "Use Directly",
  modify_first: "Modify First",
  reference_only: "Reference Only",
  do_not_use: "Do Not Use",
};

const VERDICT_ICONS = {
  pass: <CheckCircle size={13} className="text-green-400" />,
  warn: <AlertTriangle size={13} className="text-amber-400" />,
  fail: <XCircle size={13} className="text-red-400" />,
  skip: <MinusCircle size={13} className="text-[--text-muted]" />,
};

export default function RepoReviewsPage() {
  const [reviews, setReviews] = useState<RepoReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<RepoReview | null>(null);
  const [stages, setStages] = useState<ReviewStage[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [repoName, setRepoName] = useState("");
  const [branch, setBranch] = useState("main");
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      setReviews(await reviewsApi.list());
    } finally {
      setLoading(false);
    }
  }

  async function selectReview(r: RepoReview) {
    setSelected(r);
    try {
      setStages(await reviewsApi.listStages(r.id));
    } catch {
      setStages([]);
    }
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (!repoUrl.trim() || !repoName.trim()) return;
    setCreating(true);
    try {
      const r = await reviewsApi.create({ repo_url: repoUrl.trim(), repo_name: repoName.trim(), branch: branch || "main" });
      setRepoUrl(""); setRepoName(""); setBranch("main"); setShowCreate(false);
      load();
      selectReview(r);
    } finally {
      setCreating(false);
    }
  }

  const scoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-400";
    if (score >= 0.5) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div className="p-8 flex gap-6 h-[calc(100vh-0px)] overflow-hidden">
      {/* Left list */}
      <div className="w-72 flex-shrink-0 flex flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-[--text-primary]">Repo Reviews</h1>
          <Button size="sm" onClick={() => setShowCreate(true)}><Plus size={13} /></Button>
        </div>

        {showCreate && (
          <Card>
            <div className="space-y-2">
              <Input label="Repo Name (org/repo)" value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="org/repo" />
              <Input label="Repo URL" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://..." />
              <Input label="Branch" value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" />
            </div>
            <div className="flex gap-2 mt-3">
              <Button size="sm" onClick={create} loading={creating}>Create</Button>
              <Button size="sm" variant="ghost" onClick={() => setShowCreate(false)}><X size={13} /></Button>
            </div>
          </Card>
        )}

        {loading ? (
          <div className="space-y-2">{[1,2,3].map(i=><div key={i} className="h-20 bg-[--surface] border border-[--border] rounded-xl animate-pulse"/>)}</div>
        ) : reviews.length === 0 ? (
          <Card className="text-center py-8">
            <Star size={24} className="text-[--text-muted] mx-auto mb-2" />
            <p className="text-xs text-[--text-secondary]">No reviews yet</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {reviews.map((r) => (
              <Card key={r.id} onClick={() => selectReview(r)} className={selected?.id === r.id ? "border-[--accent]/50" : ""}>
                <p className="text-sm font-medium text-[--text-primary] truncate mb-1">{r.repo_name}</p>
                <div className="flex items-center gap-2">
                  <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
                  {r.classification && (
                    <Badge variant={statusBadgeVariant(r.classification)}>{CLASSIFICATION_LABELS[r.classification]}</Badge>
                  )}
                </div>
                {r.overall_score != null && (
                  <p className={`text-xs font-semibold mt-1 ${scoreColor(r.overall_score)}`}>
                    Score: {(r.overall_score * 100).toFixed(0)}%
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Right detail */}
      <div className="flex-1 overflow-y-auto">
        {!selected ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Star size={40} className="text-[--text-muted] mx-auto mb-3" />
              <p className="text-sm text-[--text-secondary]">Select a review to see pipeline details</p>
            </div>
          </div>
        ) : (
          <div>
            <div className="mb-6">
              <h2 className="text-lg font-bold text-[--text-primary]">{selected.repo_name}</h2>
              <p className="text-xs text-[--text-muted] mt-0.5">{selected.repo_url} · {selected.branch}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant={statusBadgeVariant(selected.status)}>{selected.status}</Badge>
                {selected.classification && (
                  <Badge variant={statusBadgeVariant(selected.classification)}>
                    {CLASSIFICATION_LABELS[selected.classification]}
                  </Badge>
                )}
                {selected.overall_score != null && (
                  <span className={`text-sm font-bold ${scoreColor(selected.overall_score)}`}>
                    {(selected.overall_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>

            {/* Pipeline stages */}
            <h3 className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide mb-3">5-Stage Pipeline</h3>
            {stages.length === 0 ? (
              <Card>
                <p className="text-sm text-[--text-secondary] text-center py-4">No stages recorded yet</p>
              </Card>
            ) : (
              <div className="space-y-2">
                {stages.map((stage) => (
                  <Card key={stage.id}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {VERDICT_ICONS[stage.verdict as keyof typeof VERDICT_ICONS] ?? VERDICT_ICONS.skip}
                        <div>
                          <p className="text-sm font-medium text-[--text-primary] capitalize">{stage.stage_type}</p>
                          {stage.notes && <p className="text-xs text-[--text-secondary] mt-0.5">{stage.notes}</p>}
                        </div>
                      </div>
                      <div className="text-right">
                        {stage.score != null && (
                          <span className={`text-sm font-bold ${scoreColor(stage.score)}`}>
                            {(stage.score * 100).toFixed(0)}%
                          </span>
                        )}
                        <Badge variant={statusBadgeVariant(stage.verdict)} className="ml-2">{stage.verdict}</Badge>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {selected.summary && (
              <Card className="mt-4">
                <p className="text-xs font-semibold text-[--text-muted] uppercase tracking-wide mb-2">Summary</p>
                <p className="text-sm text-[--text-secondary]">{selected.summary}</p>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
