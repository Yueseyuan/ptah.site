"use client";

import { useState } from "react";
import { researchApi, ResearchResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Search, Loader2, ChevronDown, ChevronRight, ExternalLink, BookOpen,
} from "lucide-react";

function MarkdownReport({ text }: { text: string }) {
  const lines = text.split("\n");

  return (
    <div className="space-y-2 text-sm text-[--text-primary] leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return (
            <h2 key={i} className="text-base font-bold text-[--text-primary] mt-6 mb-1 first:mt-0">
              {line.slice(3)}
            </h2>
          );
        }
        if (line.startsWith("### ")) {
          return (
            <h3 key={i} className="text-sm font-semibold text-[--text-primary] mt-4 mb-1">
              {line.slice(4)}
            </h3>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h1 key={i} className="text-lg font-bold text-[--text-primary] mt-2 mb-2">
              {line.slice(2)}
            </h1>
          );
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2 ml-3">
              <span className="text-[--text-muted] mt-0.5">•</span>
              <span>{line.slice(2)}</span>
            </div>
          );
        }
        if (/^\d+\.\s/.test(line)) {
          return (
            <div key={i} className="flex gap-2 ml-3">
              <span className="text-[--text-muted] shrink-0">{line.match(/^\d+/)![0]}.</span>
              <span>{line.replace(/^\d+\.\s/, "")}</span>
            </div>
          );
        }
        if (line.startsWith("---")) {
          return <hr key={i} className="border-[--border] my-3" />;
        }
        if (!line.trim()) {
          return <div key={i} className="h-1" />;
        }
        // Inline formatting: bold **x** and inline code `x`
        const formatted = line
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/`(.+?)`/g, '<code class="bg-[--surface-2] px-1 py-0.5 rounded text-xs font-mono">$1</code>')
          .replace(/\[Source (\d+)\]/g, '<span class="text-[--accent] text-xs font-medium">[Source $1]</span>');
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: formatted }} />
        );
      })}
    </div>
  );
}

function SubQuestions({ questions }: { questions: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-[--border] overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors"
      >
        <span className="font-medium">Research breakdown ({questions.length} sub-questions)</span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-1.5 border-t border-[--border]">
          {questions.map((q, i) => (
            <div key={i} className="flex gap-2 pt-1.5">
              <span className="text-[11px] text-[--accent] font-bold mt-0.5 shrink-0">Q{i + 1}</span>
              <span className="text-xs text-[--text-secondary]">{q}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Sources({ urls }: { urls: string[] }) {
  return (
    <div className="rounded-xl border border-[--border] p-4">
      <p className="text-xs font-semibold text-[--text-secondary] uppercase tracking-wide mb-3">
        Sources ({urls.length})
      </p>
      <div className="space-y-1.5">
        {urls.map((url, i) => {
          let display = url;
          try { display = new URL(url).hostname; } catch {}
          return (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs text-[--text-secondary] hover:text-[--accent] transition-colors group"
            >
              <span className="text-[10px] text-[--text-muted] font-mono shrink-0 w-5">[{i + 1}]</span>
              <span className="truncate">{display}</span>
              <ExternalLink size={10} className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          );
        })}
      </div>
    </div>
  );
}

const EXAMPLES = [
  "What are the most effective credit repair strategies for 2025?",
  "How does cinematic video production work for social media ads?",
  "What are the best AI tools for small business marketing?",
  "How do faceless YouTube channels monetize content?",
];

export default function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState("");

  async function run() {
    if (!question.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setError(null);

    const phases = ["Thinking…", "Searching the web…", "Reading sources…", "Synthesizing report…"];
    let pi = 0;
    setPhase(phases[0]);
    const interval = setInterval(() => {
      pi = Math.min(pi + 1, phases.length - 1);
      setPhase(phases[pi]);
    }, 12000);

    try {
      const res = await researchApi.run(question.trim());
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Research failed");
    } finally {
      clearInterval(interval);
      setLoading(false);
      setPhase("");
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run();
  }

  return (
    <div className="p-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-blue-500/15 border border-blue-500/25 flex items-center justify-center">
          <BookOpen size={18} className="text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[--text-primary]">Deep Research</h1>
          <p className="text-sm text-[--text-secondary]">Web search → source reading → cited report</p>
        </div>
      </div>

      {/* Question Input */}
      <Card className="mb-4">
        <label className="block text-xs font-medium text-[--text-secondary] mb-2">
          Research Question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          placeholder="Ask anything that requires real research…"
          rows={3}
          className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
        />
        <p className="text-[10px] text-[--text-muted] mt-1.5">Cmd/Ctrl + Enter to run</p>
      </Card>

      {/* Examples */}
      {!result && !loading && (
        <div className="mb-6">
          <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Examples</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setQuestion(ex)}
                className="text-xs px-3 py-1.5 rounded-full border border-[--border] text-[--text-secondary] hover:text-[--text-primary] hover:border-[--accent]/30 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      <Button
        onClick={run}
        loading={loading}
        disabled={!question.trim() || loading}
        className="w-full mb-6"
      >
        {loading ? (
          <><Loader2 size={14} className="animate-spin" /> {phase}</>
        ) : (
          <><Search size={14} /> Research</>
        )}
      </Button>

      {/* Error */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <SubQuestions questions={result.sub_questions} />

          <Card>
            <MarkdownReport text={result.report} />
          </Card>

          {result.sources.length > 0 && <Sources urls={result.sources} />}
        </div>
      )}
    </div>
  );
}
