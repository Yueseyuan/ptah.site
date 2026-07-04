"use client";

import { useState, useEffect } from "react";
import { channelsApi, Channel } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  MessageSquare, Plus, Trash2, Send, CheckCircle, XCircle,
  Loader2, Zap, Globe,
} from "lucide-react";

const CHANNEL_TYPES = [
  { value: "telegram", label: "Telegram Bot", icon: "✈️", desc: "Bidirectional — receive goals, reply with results" },
  { value: "discord_webhook", label: "Discord Webhook", icon: "🎮", desc: "Outbound — send notifications to a Discord channel" },
  { value: "slack_webhook", label: "Slack Webhook", icon: "💬", desc: "Outbound — send notifications to a Slack channel" },
  { value: "generic_webhook", label: "Generic Webhook", icon: "🔗", desc: "Outbound — POST JSON to any webhook URL" },
];

function TypeIcon({ type }: { type: string }) {
  const found = CHANNEL_TYPES.find((t) => t.value === type);
  return <span className="text-base">{found?.icon ?? "📡"}</span>;
}

function ChannelCard({
  channel,
  onDelete,
  onToggle,
}: {
  channel: Channel;
  onDelete: (id: number) => void;
  onToggle: (id: number, enabled: boolean) => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string | null } | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [sendMsg, setSendMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const [showWebhook, setShowWebhook] = useState(false);
  const [registering, setRegistering] = useState(false);

  async function test() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await channelsApi.test(channel.id);
      setTestResult(r);
    } finally {
      setTesting(false);
    }
  }

  async function send() {
    if (!sendMsg.trim()) return;
    setSending(true);
    setSendResult(null);
    try {
      const r = await channelsApi.send(channel.id, sendMsg.trim());
      setSendResult(r.ok ? "✓ Sent" : `✗ ${r.detail}`);
      if (r.ok) setSendMsg("");
    } finally {
      setSending(false);
    }
  }

  async function registerWebhook() {
    if (!webhookUrl.trim()) return;
    setRegistering(true);
    try {
      const r = await channelsApi.setWebhook(channel.id, webhookUrl.trim());
      setTestResult(r);
      if (r.ok) setShowWebhook(false);
    } finally {
      setRegistering(false);
    }
  }

  const typeInfo = CHANNEL_TYPES.find((t) => t.value === channel.channel_type);

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <TypeIcon type={channel.channel_type} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-[--text-primary]">{channel.name}</p>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded-full border ${
                  channel.enabled
                    ? "bg-green-500/10 border-green-500/20 text-green-400"
                    : "bg-[--surface-2] border-[--border] text-[--text-muted]"
                }`}
              >
                {channel.enabled ? "active" : "paused"}
              </span>
            </div>
            <p className="text-xs text-[--text-muted]">{typeInfo?.label ?? channel.channel_type}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={test}
            className="p-1.5 rounded-lg text-[--text-muted] hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
            title="Test connection"
          >
            {testing ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
          </button>
          <button
            onClick={() => onToggle(channel.id, !channel.enabled)}
            className={`p-1.5 rounded-lg transition-colors ${
              channel.enabled
                ? "text-green-400 hover:text-[--text-muted] hover:bg-[--surface-2]"
                : "text-[--text-muted] hover:text-green-400 hover:bg-green-500/10"
            }`}
            title={channel.enabled ? "Pause" : "Activate"}
          >
            {channel.enabled ? <CheckCircle size={13} /> : <XCircle size={13} />}
          </button>
          <button
            onClick={() => onDelete(channel.id)}
            className="p-1.5 rounded-lg text-[--text-muted] hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {testResult && (
        <p className={`mt-2 text-xs ${testResult.ok ? "text-green-400" : "text-red-400"}`}>
          {testResult.ok ? "✓" : "✗"} {testResult.detail}
        </p>
      )}

      {/* Telegram: register webhook button */}
      {channel.channel_type === "telegram" && (
        <div className="mt-3 border-t border-[--border] pt-3">
          {!showWebhook ? (
            <button
              onClick={() => setShowWebhook(true)}
              className="text-xs text-[--accent] hover:opacity-80 transition-opacity"
            >
              Register webhook URL →
            </button>
          ) : (
            <div className="flex gap-2">
              <input
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://your-domain.com/api/v1/channels/telegram/webhook"
                className="flex-1 bg-[--bg] border border-[--border] rounded-lg px-3 py-1.5 text-xs text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
              />
              <button
                onClick={registerWebhook}
                disabled={registering}
                className="px-3 py-1.5 bg-[--accent] text-white text-xs rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {registering ? <Loader2 size={11} className="animate-spin" /> : "Set"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Quick send */}
      <div className="mt-3 border-t border-[--border] pt-3 flex gap-2">
        <input
          value={sendMsg}
          onChange={(e) => setSendMsg(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Send a test message…"
          className="flex-1 bg-[--bg] border border-[--border] rounded-lg px-3 py-1.5 text-xs text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
        />
        <button
          onClick={send}
          disabled={!sendMsg.trim() || sending}
          className="p-2 bg-[--accent] text-white rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
        </button>
      </div>
      {sendResult && (
        <p className={`mt-1 text-[11px] ${sendResult.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>
          {sendResult}
        </p>
      )}
    </Card>
  );
}

function AddChannelForm({ onAdd }: { onAdd: (ch: Channel) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("telegram");
  const [botToken, setBotToken] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [allowedChats, setAllowedChats] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildConfig(): Record<string, unknown> {
    if (type === "telegram") {
      const config: Record<string, unknown> = { bot_token: botToken };
      if (allowedChats.trim()) {
        config.allowed_chat_ids = allowedChats.split(",").map((s) => s.trim()).filter(Boolean);
      }
      return config;
    }
    return { webhook_url: webhookUrl };
  }

  async function submit() {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const ch = await channelsApi.create({
        name: name.trim(),
        channel_type: type,
        config: buildConfig(),
        enabled: true,
      });
      onAdd(ch);
      setName(""); setBotToken(""); setWebhookUrl(""); setAllowedChats(""); setOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create channel");
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
        <Plus size={14} /> Add channel
      </button>
    );
  }

  const isTelegram = type === "telegram";

  return (
    <Card>
      <p className="text-sm font-semibold text-[--text-primary] mb-4">New Channel</p>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-1">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Telegram Bot"
            className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-[--text-secondary] mb-2">Type</label>
          <div className="grid grid-cols-2 gap-2">
            {CHANNEL_TYPES.map((ct) => (
              <button
                key={ct.value}
                onClick={() => setType(ct.value)}
                className={`flex items-start gap-2 p-2.5 rounded-lg border text-left transition-colors ${
                  type === ct.value
                    ? "border-[--accent]/50 bg-[--accent-muted]"
                    : "border-[--border] hover:border-[--accent]/30"
                }`}
              >
                <span className="text-base mt-0.5">{ct.icon}</span>
                <div>
                  <p className="text-xs font-medium text-[--text-primary]">{ct.label}</p>
                  <p className="text-[10px] text-[--text-muted] leading-tight">{ct.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {isTelegram ? (
          <>
            <div>
              <label className="block text-xs font-medium text-[--text-secondary] mb-1">
                Bot Token <span className="text-[--text-muted]">(from @BotFather)</span>
              </label>
              <input
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="1234567890:ABCdefGHIjklMNOpqrSTUvwxyz"
                type="password"
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[--text-secondary] mb-1">
                Allowed Chat IDs <span className="text-[--text-muted]">(optional, comma-separated)</span>
              </label>
              <input
                value={allowedChats}
                onChange={(e) => setAllowedChats(e.target.value)}
                placeholder="123456789, -987654321"
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
              />
              <p className="text-[10px] text-[--text-muted] mt-1">
                Leave blank to allow all chats. After saving, register a webhook URL to go live.
              </p>
            </div>
          </>
        ) : (
          <div>
            <label className="block text-xs font-medium text-[--text-secondary] mb-1">Webhook URL</label>
            <input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/…"
              className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors"
            />
          </div>
        )}
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

      <div className="flex gap-2 mt-4">
        <Button
          onClick={submit}
          loading={loading}
          disabled={!name.trim() || loading}
          className="flex-1"
        >
          <MessageSquare size={13} /> Add Channel
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

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    channelsApi.list().then(setChannels).finally(() => setLoading(false));
  }, []);

  async function deleteChannel(id: number) {
    await channelsApi.delete(id);
    setChannels((prev) => prev.filter((c) => c.id !== id));
  }

  async function toggleChannel(id: number, enabled: boolean) {
    const updated = await channelsApi.update(id, { enabled });
    setChannels((prev) => prev.map((c) => (c.id === id ? updated : c)));
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center">
          <MessageSquare size={18} className="text-purple-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">Channels</h1>
          <p className="text-sm text-[--text-secondary]">Telegram, Discord, Slack — send and receive with Chief</p>
        </div>
      </div>

      <AddChannelForm onAdd={(ch) => setChannels((prev) => [ch, ...prev])} />

      <div className="mt-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-[--text-muted]">
            <Loader2 size={18} className="animate-spin mr-2" /> Loading…
          </div>
        ) : channels.length === 0 ? (
          <div className="text-center py-12 text-sm text-[--text-muted]">
            <Globe size={24} className="mx-auto mb-3 opacity-30" />
            No channels configured yet. Add one to connect Chief to your messaging apps.
          </div>
        ) : (
          channels.map((ch) => (
            <ChannelCard key={ch.id} channel={ch} onDelete={deleteChannel} onToggle={toggleChannel} />
          ))
        )}
      </div>
    </div>
  );
}
