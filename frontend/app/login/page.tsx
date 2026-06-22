"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await authApi.login(email, password);
      setToken(data.access_token);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[--bg] px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-[--accent] mb-4">
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <h1 className="text-xl font-bold text-[--text-primary]">APEX AI</h1>
          <p className="text-sm text-[--text-muted] mt-1">Sign in to your workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[--surface] border border-[--border] rounded-2xl p-6 space-y-4">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />

          {error && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full justify-center">
            Sign in
          </Button>

          <p className="text-center text-xs text-[--text-muted]">
            No account?{" "}
            <Link href="/register" className="text-[--accent] hover:underline">
              Register
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
