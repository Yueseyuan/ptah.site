"use client";

import { useEffect, useState } from "react";
import {
  mediaStudioApi,
  VideoGenerateResult,
  VoiceoverResult,
  ImageGenerateResult,
  MusicResult,
  HiggsfieldBalance,
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Film, Mic, Loader2, CheckCircle2, XCircle, Copy, Download,
  Play, Coins, ChevronDown, Image, Music,
} from "lucide-react";

type Tab = "video" | "voiceover" | "image" | "music";

const VOICES = [
  { id: "Sterling", label: "Sterling", desc: "Professional male, authoritative" },
  { id: "Harrison", label: "Harrison", desc: "Warm male, conversational" },
  { id: "Arthur", label: "Arthur", desc: "Mature male, distinguished" },
  { id: "Tallulah", label: "Tallulah", desc: "Expressive female, energetic" },
  { id: "Vesper", label: "Vesper", desc: "Smooth female, sophisticated" },
  { id: "Roman", label: "Roman", desc: "Deep male, cinematic" },
  { id: "Julian", label: "Julian", desc: "Clear male, friendly" },
];

const GENRES = ["auto", "action", "suspense", "spectacle", "intimate", "comedy", "horror", "western"];

const IMAGE_MODELS = [
  { id: "nano_banana_2", label: "Nano Banana Pro", desc: "Fast, versatile" },
  { id: "flux_2", label: "FLUX.2", desc: "High quality" },
  { id: "gpt_image_2", label: "GPT Image 2", desc: "GPT-based" },
  { id: "cinematic_studio_2_5", label: "Cinematic 2.5", desc: "Cinematic style" },
];

const TABS: { id: Tab; label: string; Icon: React.ElementType }[] = [
  { id: "video", label: "Video", Icon: Film },
  { id: "image", label: "Image", Icon: Image },
  { id: "voiceover", label: "Voiceover", Icon: Mic },
  { id: "music", label: "Music & SFX", Icon: Music },
];

function BalanceBadge({ balance }: { balance: HiggsfieldBalance | null }) {
  if (!balance) return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] bg-[--surface-2] text-[--text-muted] border border-[--border]">
      <Loader2 size={10} className="animate-spin" /> Checking…
    </span>
  );
  if (!balance.ok) return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
      <Coins size={10} /> Setup required
    </span>
  );
  const credits = balance.credits ?? balance.balance ?? 0;
  return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] bg-green-500/10 text-green-400 border border-green-500/20">
      <Coins size={10} /> {credits} credits
    </span>
  );
}

function SetupBanner({ balance }: { balance: HiggsfieldBalance | null }) {
  if (!balance || balance.ok) return null;
  return (
    <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
      <p className="text-sm font-medium text-amber-300 mb-2">Media provider not configured</p>
      <p className="text-xs text-amber-400/80 mb-3">
        Add your Muapi.ai API key to the backend <code className="font-mono bg-amber-500/10 px-1 rounded">.env</code> file, then restart the backend:
      </p>
      <pre className="text-[11px] font-mono bg-black/20 border border-amber-500/20 rounded-lg px-3 py-2 mb-3 text-amber-200 overflow-x-auto whitespace-pre">{"MUAPI_API_KEY=your_key_here"}</pre>
      <p className="text-[10px] text-amber-400/60">
        Get a free API key at <span className="text-amber-300">muapi.ai</span>. Supports video, image, voiceover, music, and SFX generation.
      </p>
      {balance.error && (
        <p className="mt-3 text-[10px] font-mono text-amber-500/60 break-all">{balance.error}</p>
      )}
    </div>
  );
}

function ResultCard({ url, label, duration }: { url: string; label: string; duration?: number | null }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="rounded-xl border border-green-500/25 bg-green-500/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 size={14} className="text-green-400" />
        <span className="text-sm font-medium text-green-300">{label} ready</span>
        {duration != null && (
          <span className="text-[10px] text-green-400/60 ml-auto">{duration.toFixed(1)}s</span>
        )}
      </div>
      <div className="font-mono text-[11px] text-[--text-secondary] bg-[--bg] rounded-lg px-3 py-2 mb-3 break-all border border-[--border]">
        {url}
      </div>
      <div className="flex gap-2">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[--surface-2] border border-[--border] text-[--text-secondary] hover:text-[--text-primary] transition-colors"
        >
          <Play size={11} /> Preview
        </a>
        <a
          href={url}
          download
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[--surface-2] border border-[--border] text-[--text-secondary] hover:text-[--text-primary] transition-colors"
        >
          <Download size={11} /> Download
        </a>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[--surface-2] border border-[--border] text-[--text-secondary] hover:text-[--text-primary] transition-colors ml-auto"
        >
          <Copy size={11} /> {copied ? "Copied!" : "Copy URL"}
        </button>
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
      <XCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
      <p className="text-xs text-red-400">{message}</p>
    </div>
  );
}

export default function MediaStudioPage() {
  const [tab, setTab] = useState<Tab>("video");
  const [balance, setBalance] = useState<HiggsfieldBalance | null>(null);

  // Video state
  const [videoPrompt, setVideoPrompt] = useState("");
  const [duration, setDuration] = useState(6);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [genre, setGenre] = useState("auto");
  const [sound, setSound] = useState<"on" | "off">("on");
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult] = useState<VideoGenerateResult | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);

  // Image state
  const [imagePrompt, setImagePrompt] = useState("");
  const [imageModel, setImageModel] = useState("nano_banana_2");
  const [imageAspect, setImageAspect] = useState("1:1");
  const [imageLoading, setImageLoading] = useState(false);
  const [imageResult, setImageResult] = useState<ImageGenerateResult | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  // Voiceover state
  const [script, setScript] = useState("");
  const [voice, setVoice] = useState("Sterling");
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceoverResult | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  // Music / SFX state
  const [musicPrompt, setMusicPrompt] = useState("");
  const [musicDuration, setMusicDuration] = useState(12);
  const [sfxPrompt, setSfxPrompt] = useState("");
  const [musicLoading, setMusicLoading] = useState(false);
  const [sfxLoading, setSfxLoading] = useState(false);
  const [musicResult, setMusicResult] = useState<MusicResult | null>(null);
  const [sfxResult, setSfxResult] = useState<MusicResult | null>(null);
  const [musicError, setMusicError] = useState<string | null>(null);
  const [sfxError, setSfxError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchBalance() {
      try {
        setBalance(await mediaStudioApi.balance());
      } catch {
        setBalance({ ok: false });
      }
    }
    void fetchBalance();
  }, []);

  async function generateVideo() {
    if (!videoPrompt.trim() || videoLoading) return;
    setVideoLoading(true);
    setVideoResult(null);
    setVideoError(null);
    try {
      const res = await mediaStudioApi.generateVideo({
        prompt: videoPrompt.trim(),
        duration,
        aspect_ratio: aspectRatio,
        genre,
        sound,
      });
      setVideoResult(res);
    } catch (e: unknown) {
      setVideoError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setVideoLoading(false);
    }
  }

  async function generateImage() {
    if (!imagePrompt.trim() || imageLoading) return;
    setImageLoading(true);
    setImageResult(null);
    setImageError(null);
    try {
      const res = await mediaStudioApi.generateImage({
        prompt: imagePrompt.trim(),
        model: imageModel,
        aspect_ratio: imageAspect,
      });
      setImageResult(res);
    } catch (e: unknown) {
      setImageError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setImageLoading(false);
    }
  }

  async function generateVoiceover() {
    if (!script.trim() || voiceLoading) return;
    setVoiceLoading(true);
    setVoiceResult(null);
    setVoiceError(null);
    try {
      const res = await mediaStudioApi.generateVoiceover({ text: script.trim(), voice });
      setVoiceResult(res);
    } catch (e: unknown) {
      setVoiceError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setVoiceLoading(false);
    }
  }

  async function generateMusic() {
    if (!musicPrompt.trim() || musicLoading) return;
    setMusicLoading(true);
    setMusicResult(null);
    setMusicError(null);
    try {
      const res = await mediaStudioApi.generateMusic({ prompt: musicPrompt.trim(), duration: musicDuration });
      setMusicResult(res);
    } catch (e: unknown) {
      setMusicError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setMusicLoading(false);
    }
  }

  async function generateSfx() {
    if (!sfxPrompt.trim() || sfxLoading) return;
    setSfxLoading(true);
    setSfxResult(null);
    setSfxError(null);
    try {
      const res = await mediaStudioApi.generateSfx({ prompt: sfxPrompt.trim() });
      setSfxResult(res);
    } catch (e: unknown) {
      setSfxError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setSfxLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center">
            <Film size={18} className="text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[--text-primary]">Media Studio</h1>
            <p className="text-sm text-[--text-secondary]">Generate videos, images, and audio directly</p>
          </div>
        </div>
        <BalanceBadge balance={balance} />
      </div>

      <SetupBanner balance={balance} />

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-[--surface] rounded-xl border border-[--border]">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
              tab === id
                ? "bg-[--accent] text-white shadow-sm"
                : "text-[--text-secondary] hover:text-[--text-primary]"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Video Tab */}
      {tab === "video" && (
        <div className="space-y-4">
          <Card>
            <label className="block text-xs font-medium text-[--text-secondary] mb-2">
              Scene Description
            </label>
            <textarea
              value={videoPrompt}
              onChange={(e) => setVideoPrompt(e.target.value)}
              disabled={videoLoading}
              placeholder="Cinematic close-up of hands receiving car keys at a dealership, golden hour lighting, no faces shown, celebration mood…"
              rows={4}
              className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
            />
          </Card>

          <div className="grid grid-cols-2 gap-3">
            <Card className="py-3">
              <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Aspect Ratio</p>
              <div className="flex gap-1.5">
                {["9:16", "16:9", "1:1"].map((r) => (
                  <button
                    key={r}
                    onClick={() => setAspectRatio(r)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      aspectRatio === r
                        ? "bg-[--accent] text-white"
                        : "bg-[--surface-2] text-[--text-secondary] border border-[--border] hover:text-[--text-primary]"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </Card>

            <Card className="py-3">
              <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">
                Duration — {duration}s
              </p>
              <input
                type="range"
                min={3}
                max={12}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="w-full accent-[--accent]"
              />
              <div className="flex justify-between text-[10px] text-[--text-muted] mt-1">
                <span>3s</span><span>12s</span>
              </div>
            </Card>

            <Card className="py-3">
              <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Genre</p>
              <div className="relative">
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full appearance-none bg-[--bg] border border-[--border] rounded-lg px-3 py-1.5 text-sm text-[--text-primary] focus:outline-none focus:border-[--accent]/50 pr-8"
                >
                  {GENRES.map((g) => (
                    <option key={g} value={g}>{g.charAt(0).toUpperCase() + g.slice(1)}</option>
                  ))}
                </select>
                <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[--text-muted] pointer-events-none" />
              </div>
            </Card>

            <Card className="py-3">
              <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Sound</p>
              <div className="flex gap-1.5">
                {(["on", "off"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setSound(s)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      sound === s
                        ? "bg-[--accent] text-white"
                        : "bg-[--surface-2] text-[--text-secondary] border border-[--border] hover:text-[--text-primary]"
                    }`}
                  >
                    {s === "on" ? "🔊 On" : "🔇 Off"}
                  </button>
                ))}
              </div>
            </Card>
          </div>

          <Button
            onClick={generateVideo}
            loading={videoLoading}
            disabled={!videoPrompt.trim() || videoLoading}
            className="w-full"
          >
            {videoLoading ? (
              <><Loader2 size={14} className="animate-spin" /> Generating… (1–3 min)</>
            ) : (
              <><Film size={14} /> Generate Video</>
            )}
          </Button>

          {videoError && <ErrorBanner message={videoError} />}
          {videoResult?.url && <ResultCard url={videoResult.url} label="Video" />}
        </div>
      )}

      {/* Image Tab */}
      {tab === "image" && (
        <div className="space-y-4">
          <Card>
            <label className="block text-xs font-medium text-[--text-secondary] mb-2">
              Image Description
            </label>
            <textarea
              value={imagePrompt}
              onChange={(e) => setImagePrompt(e.target.value)}
              disabled={imageLoading}
              placeholder="Professional portrait of a confident entrepreneur in a modern office, dramatic side lighting, shallow depth of field…"
              rows={4}
              className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
            />
          </Card>

          <Card>
            <p className="text-xs font-medium text-[--text-secondary] mb-3">Model</p>
            <div className="space-y-1.5">
              {IMAGE_MODELS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setImageModel(m.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
                    imageModel === m.id
                      ? "bg-[--accent]/15 border border-[--accent]/30"
                      : "bg-[--surface-2] border border-[--border] hover:border-[--accent]/20"
                  }`}
                >
                  <span className={`text-sm font-medium ${imageModel === m.id ? "text-[--accent]" : "text-[--text-primary]"}`}>
                    {m.label}
                  </span>
                  <span className="text-[10px] text-[--text-muted]">{m.desc}</span>
                </button>
              ))}
            </div>
          </Card>

          <Card className="py-3">
            <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">Aspect Ratio</p>
            <div className="flex gap-1.5">
              {["1:1", "16:9", "9:16", "4:3", "3:4"].map((r) => (
                <button
                  key={r}
                  onClick={() => setImageAspect(r)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    imageAspect === r
                      ? "bg-[--accent] text-white"
                      : "bg-[--surface-2] text-[--text-secondary] border border-[--border] hover:text-[--text-primary]"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </Card>

          <Button
            onClick={generateImage}
            loading={imageLoading}
            disabled={!imagePrompt.trim() || imageLoading}
            className="w-full"
          >
            {imageLoading ? (
              <><Loader2 size={14} className="animate-spin" /> Generating…</>
            ) : (
              <><Image size={14} /> Generate Image</>
            )}
          </Button>

          {imageError && <ErrorBanner message={imageError} />}
          {imageResult?.url && <ResultCard url={imageResult.url} label="Image" />}
        </div>
      )}

      {/* Voiceover Tab */}
      {tab === "voiceover" && (
        <div className="space-y-4">
          <Card>
            <label className="block text-xs font-medium text-[--text-secondary] mb-2">
              Script
            </label>
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              disabled={voiceLoading}
              placeholder="Your credit score doesn't define your future. At Cruel and Associates, we've helped thousands of clients raise their scores across all three bureaus…"
              rows={5}
              className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
            />
            <p className="text-[10px] text-[--text-muted] mt-1.5">{script.length} characters</p>
          </Card>

          <Card>
            <p className="text-xs font-medium text-[--text-secondary] mb-3">Voice</p>
            <div className="space-y-1.5">
              {VOICES.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setVoice(v.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
                    voice === v.id
                      ? "bg-[--accent]/15 border border-[--accent]/30"
                      : "bg-[--surface-2] border border-[--border] hover:border-[--accent]/20"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Mic size={12} className={voice === v.id ? "text-[--accent]" : "text-[--text-muted]"} />
                    <span className={`text-sm font-medium ${voice === v.id ? "text-[--accent]" : "text-[--text-primary]"}`}>
                      {v.label}
                    </span>
                  </div>
                  <span className="text-[10px] text-[--text-muted]">{v.desc}</span>
                </button>
              ))}
            </div>
          </Card>

          <Button
            onClick={generateVoiceover}
            loading={voiceLoading}
            disabled={!script.trim() || voiceLoading}
            className="w-full"
          >
            {voiceLoading ? (
              <><Loader2 size={14} className="animate-spin" /> Generating…</>
            ) : (
              <><Mic size={14} /> Generate Voiceover</>
            )}
          </Button>

          {voiceError && <ErrorBanner message={voiceError} />}
          {voiceResult?.url && (
            <ResultCard url={voiceResult.url} label="Voiceover" duration={voiceResult.duration} />
          )}
        </div>
      )}

      {/* Music & SFX Tab */}
      {tab === "music" && (
        <div className="space-y-6">
          {/* Background Music section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 rounded-full bg-[--accent]" />
              <p className="text-sm font-semibold text-[--text-primary]">Background Music</p>
              <span className="text-[10px] text-[--text-muted] ml-1">via Sonilo</span>
            </div>

            <Card>
              <label className="block text-xs font-medium text-[--text-secondary] mb-2">
                Music Description
              </label>
              <textarea
                value={musicPrompt}
                onChange={(e) => setMusicPrompt(e.target.value)}
                disabled={musicLoading}
                placeholder="Cinematic orchestral build, hopeful and triumphant, rising strings with percussion, suitable for a brand promo…"
                rows={3}
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
              />
            </Card>

            <Card className="py-3">
              <p className="text-[10px] text-[--text-muted] uppercase tracking-wide mb-2 font-medium">
                Duration — {musicDuration}s
              </p>
              <input
                type="range"
                min={4}
                max={60}
                step={4}
                value={musicDuration}
                onChange={(e) => setMusicDuration(Number(e.target.value))}
                className="w-full accent-[--accent]"
              />
              <div className="flex justify-between text-[10px] text-[--text-muted] mt-1">
                <span>4s</span><span>60s</span>
              </div>
            </Card>

            <Button
              onClick={generateMusic}
              loading={musicLoading}
              disabled={!musicPrompt.trim() || musicLoading}
              className="w-full"
            >
              {musicLoading ? (
                <><Loader2 size={14} className="animate-spin" /> Generating…</>
              ) : (
                <><Music size={14} /> Generate Music</>
              )}
            </Button>

            {musicError && <ErrorBanner message={musicError} />}
            {musicResult?.url && (
              <ResultCard url={musicResult.url} label="Music" duration={musicResult.duration} />
            )}
          </div>

          <div className="border-t border-[--border]" />

          {/* Sound Effects section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 rounded-full bg-purple-400" />
              <p className="text-sm font-semibold text-[--text-primary]">Sound Effects</p>
              <span className="text-[10px] text-[--text-muted] ml-1">via Mirelo</span>
            </div>

            <Card>
              <label className="block text-xs font-medium text-[--text-secondary] mb-2">
                Sound Description
              </label>
              <textarea
                value={sfxPrompt}
                onChange={(e) => setSfxPrompt(e.target.value)}
                disabled={sfxLoading}
                placeholder="Glass breaking in a large marble hallway, reverb, slight echo…"
                rows={3}
                className="w-full bg-[--bg] border border-[--border] rounded-lg px-3 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] resize-none focus:outline-none focus:border-[--accent]/50 transition-colors disabled:opacity-60"
              />
            </Card>

            <Button
              onClick={generateSfx}
              loading={sfxLoading}
              disabled={!sfxPrompt.trim() || sfxLoading}
              className="w-full"
            >
              {sfxLoading ? (
                <><Loader2 size={14} className="animate-spin" /> Generating…</>
              ) : (
                <><Music size={14} /> Generate SFX</>
              )}
            </Button>

            {sfxError && <ErrorBanner message={sfxError} />}
            {sfxResult?.url && (
              <ResultCard url={sfxResult.url} label="SFX" duration={sfxResult.duration} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
