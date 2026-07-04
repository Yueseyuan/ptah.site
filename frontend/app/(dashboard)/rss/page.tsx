"use client";

import { useState, useEffect } from "react";
import { rssApi, RssFeed, RssPreviewItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Rss, Plus, Trash2, Play, Eye, CheckCircle, XCircle,
  Clock, AlertCircle, ChevronDown, ChevronRight, Loader2,
} from "lucide-react";

const DEFAULT_GOAL = `Research and summarize this article: {title}

URL: {link}

Summary: {summary}`;

function StatusDot({ enabled }: { enabled: boolean }) {
  return (
    <span
      className={`w-2 h-2 rounded-full shrink-0 ${enabled ? "bg-green-400" : "bg-[--text-muted]"}`}
    />
  );
}

function FeedCard({
  feed,
  onDelete,
  onToggle,
  onCheckNow,
}: {
  feed: RssFeed;
  onDelete: (id: number) => void;
  onToggle: (id: number, enabled: boolean) => void;
  onCheckNow: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [items, setItems] = useState<RssPreviewItem[]>([]);
  const [checking, setChecking] = useState(false);

  async function preview() {
    setPreviewing(true);
    try {
      const data = await rssApi.preview(feed.id);
      setItems(data);
      setExpanded(true);
    } catch {
      // ignore
    } finally {
      setPreviewing(false);
    }
  }

  async function checkNow() {
    setChecking(true);
    try {
      await onCheckNow(feed.id);
    } finally {
      setChecking(false);
    }
  }

  const lastChecked = feed.last_checked_at
    ? new Date(feed.last_checked_at).toLocaleString()
    : "Never";

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <StatusDot enabled={feed.enabled} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-[--text-primary] truncate">{feed.name}</p>
            <p className="text-xs text-[--text-muted] truncate">{feed.url}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={preview}
            className="p-1.5 rounded-lg text-[--text-muted] hover:text-[--text-primary] hover:bg-[--surface-2] transition-colors"
            title="Preview items"
          >
            {previewing ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
          </button>
          <button
            onClick={checkNow}
            className="p-1.5 rounded-lg text-[--text-muted] hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
            title="Poll now"
          >
            {checking ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          </button>
          <button
            onClick={() => onToggle(feed.id, !feed.enabled)}
            className={`p-1.5 rounded-lg transition-colors ${
              feed.enabled
                ? "text-green-400 hover:text-[--text-muted] hover:bg-[--surface-2]"
                : "text-[--text-muted] hover:text-green-400 hover:bg-green-500/10"
            }`}
            title={feed.enabled ? "Disable" : "Enable"}
          >
            {feed.enabled ? <CheckCircle size={13} /> : <XCircle size={13} />}
          </button>
          <button
            onClick={() => onDelete(feed.id)}
            className="p-1.5 rounded-lg text-[--text-muted] hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Meta row */}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[--text-muted]">
        <span className="flex items-center gap-1">
          <Clock size={10} /> Every {feed.poll_interval_minutes}m
        </span>
        <span>Last checked: {lastChecked}</span>
        <span className="text-green-400">{feed.run_count} triggered</span>
        {feed.error_count > 0 && (
          <span className="flex items-center gap-1 text-red-400">
            <AlertCircle size={10} /> {feed.error_count} errors
          </span>
        )}
      </div>

      {feed.last_error && (
        <p className="mt-1.5 text-[10px] text-red-400 truncate">{feed.last_error}</p>
      )}

      {/* Preview items */}
      {items.length > 0 && (
        <div className="mt-3 border-t border-[--border]">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center gap-1.5 pt-3 text-xs text-[--text-muted] hover:text-[--text-primary] transition-colors"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {items.length} latest items
          </button>
          {expanded && (
            <div className="mt-2 space-y-1.5">
              {items.map((item) => (
                <a
                  key={item.guid}
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-[--text-secondary] hover:text-[--accent] transition-colors truncate"
                >
                  {item.title || item.link}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function AddFeedForm({ onAdd }: { onAdd: (feed: RssFeed) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [goalTemplate, setGoalTemplate] = useState(DEFAULT_GOAL);
  const [interval, setInterval] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || !url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const feed = await rssApi.create({
        name: name.trim(),
        url: url.trim(),
        goal_template: goalTemplate.trim(),
        poll_interval_minutes: interval,
        enabled: true,
      });
      onAdd(feed);
      setName("");
      setUrl("");
      setGoalTemplate(DEFAULT_GOAL);
      setInterval(60);
      setOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create feed");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2 px-4 py-3 rounded-xl border border-dashed border-[--border] text-sm text-[--text-muted] hover:text-[--text-primary] hover:border-[--accent]/40 transition-colors"
      >
        <Plus size={14} />
        Add RSS feed
      </button>
    );
  }

  return (
    <Card>
      <p className="text-sm font-semibold text-[--text-primary] mb-4">New RSS Feed</p>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-1">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="TechCrunch AI"
            className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-1">Feed URL</label>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://techcrunch.com/feed/"
            className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-1">
            Poll interval (minutes)
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={5}
              max={1440}
              step={5}
              value={interval}
              onChange={(e) => setInterval(Number(e.target.value))}
              className="flex-1 accent-[--accent]"
            />
            <span className="text-xs text-[--text-primary] w-16 text-right">
              {interval < 60 ? `${interval}m` : `${(interval / 60).toFixed(1)}h`}
            </span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-1">
            Chief goal template
          </label>
          <p className="text-[10px] text-[--text-muted] mb-1.5">
            Use <code className="bg-[--surface-2] px-1 rounded text-[10px]">{"{{title}}"}</code>,{" "}
            <code className="bg-[--surface-2] px-1 rounded text-[10px]">{"{{link}}"}</code>,{" "}
            <code className="bg-[--surface-2] px-1 rounded text-[10px]">{"{{summary}}"}</code> as placeholders.
          </p>
          <textarea
            value={goalTemplate}
            onChange={(e) => setGoalTemplate(e.target.value)}
            rows={4}
            className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-xs text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors font-mono"
          />
        </div>
      </div>

      {error && (
        <p className="mt-2 text-xs text-red-400">{error}</p>
      )}

      <div className="flex gap-2 mt-4">
        <Button onClick={submit} loading={loading} disabled={!name.trim() || !url.trim() || loading} className="flex-1">
          <Rss size={13} /> Add Feed
        </Button>
        <button
          onClick={() => setOpen(false)}
          className="px-4 py-2 text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors"
        >
          Cancel
        </button>
      </div>
    </Card>
  );
}

export default function RssPage() {
  const [feeds, setFeeds] = useState<RssFeed[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    rssApi.list().then(setFeeds).finally(() => setLoading(false));
  }, []);

  function addFeed(feed: RssFeed) {
    setFeeds((prev) => [feed, ...prev]);
  }

  async function deleteFeed(id: number) {
    await rssApi.delete(id);
    setFeeds((prev) => prev.filter((f) => f.id !== id));
  }

  async function toggleFeed(id: number, enabled: boolean) {
    const updated = await rssApi.update(id, { enabled });
    setFeeds((prev) => prev.map((f) => (f.id === id ? updated : f)));
  }

  async function checkNow(id: number) {
    const updated = await rssApi.checkNow(id);
    setFeeds((prev) => prev.map((f) => (f.id === id ? updated : f)));
  }

  return (
    <div className="p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-orange-500/15 border border-orange-500/25 flex items-center justify-center">
          <Rss size={18} className="text-orange-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">RSS Polling</h1>
          <p className="text-sm text-[--text-secondary]">Auto-trigger Chief when new content appears</p>
        </div>
      </div>

      <AddFeedForm onAdd={addFeed} />

      <div className="mt-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-[--text-muted]">
            <Loader2 size={18} className="animate-spin mr-2" /> Loading feeds…
          </div>
        ) : feeds.length === 0 ? (
          <div className="text-center py-12 text-[--text-muted] text-sm">
            No RSS feeds yet. Add one above.
          </div>
        ) : (
          feeds.map((feed) => (
            <FeedCard
              key={feed.id}
              feed={feed}
              onDelete={deleteFeed}
              onToggle={toggleFeed}
              onCheckNow={checkNow}
            />
          ))
        )}
      </div>
    </div>
  );
}
