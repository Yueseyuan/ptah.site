"use client";

import { useState } from "react";
import { youtubeApi, TranscribeResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PlaySquare, Loader2, Copy, Check, Captions, Mic } from "lucide-react";

const EXAMPLES = [
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "https://youtu.be/aircAruvnKk",
];

function MethodBadge({ method }: { method: string | null }) {
  if (!method) return null;
  const isCaptions = method === "captions";
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${
        isCaptions
          ? "bg-green-500/10 border-green-500/20 text-green-400"
          : "bg-blue-500/10 border-blue-500/20 text-blue-400"
      }`}
    >
      {isCaptions ? <Captions size={10} /> : <Mic size={10} />}
      {isCaptions ? "Auto-captions" : "Whisper AI"}
    </span>
  );
}

export default function YouTubePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TranscribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function run() {
    if (!url.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await youtubeApi.transcribe(url.trim());
      if (res.ok) {
        setResult(res);
      } else {
        setError(res.error ?? "Transcription failed");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run();
  }

  async function copyTranscript() {
    if (!result?.transcript) return;
    await navigator.clipboard.writeText(result.transcript);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const charCount = result?.transcript?.length ?? 0;
  const wordCount = result?.transcript?.trim().split(/\s+/).length ?? 0;

  return (
    <div className="p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/25 flex items-center justify-center">
          <PlaySquare size={18} className="text-red-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">YouTube Transcription</h1>
          <p className="text-sm text-[--text-secondary]">Paste a URL → get the full transcript</p>
        </div>
      </div>

      {/* URL Input */}
      <Card className="mb-4">
        <label className="block text-xs font-medium text-[--text-secondary] mb-2">
          YouTube URL
        </label>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          placeholder="https://www.youtube.com/watch?v=..."
          className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
        />
        <p className="text-[10px] text-[--text-muted] mt-1.5">
          Works with youtube.com and youtu.be links · Cmd/Ctrl + Enter to run
        </p>
      </Card>

      {/* Examples */}
      {!result && !loading && (
        <div className="mb-6">
          <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Examples</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setUrl(ex)}
                className="text-xs px-3 py-1.5 rounded-full border border-[--border] text-[--text-secondary] hover:text-[--text-primary] hover:border-[--accent]/30 transition-colors font-mono"
              >
                {ex.replace("https://", "")}
              </button>
            ))}
          </div>
        </div>
      )}

      <Button
        onClick={run}
        loading={loading}
        disabled={!url.trim() || loading}
        className="w-full mb-6"
      >
        {loading ? (
          <><Loader2 size={14} className="animate-spin" /> Transcribing…</>
        ) : (
          <><PlaySquare size={14} /> Transcribe</>
        )}
      </Button>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* Result */}
      {result && result.transcript && (
        <div className="space-y-3">
          {/* Meta bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MethodBadge method={result.method} />
              {result.video_id && (
                <span className="text-[10px] text-[--text-muted] font-mono">{result.video_id}</span>
              )}
            </div>
            <span className="text-[10px] text-[--text-muted]">
              {wordCount.toLocaleString()} words · {charCount.toLocaleString()} chars
            </span>
          </div>

          <Card>
            {/* Copy button */}
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold text-[--text-secondary] uppercase tracking-wide">
                Transcript
              </p>
              <button
                onClick={copyTranscript}
                className="flex items-center gap-1.5 text-xs text-[--text-muted] hover:text-[--text-primary] transition-colors"
              >
                {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="text-sm text-[--text-primary] leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
              {result.transcript}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
