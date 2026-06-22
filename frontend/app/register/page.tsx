"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
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
      await authApi.register(email, password);
      router.push("/login");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[--bg] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-[--accent] mb-4">
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <h1 className="text-xl font-bold text-[--text-primary]">Create account</h1>
          <p className="text-sm text-[--text-muted] mt-1">Join APEX AI workspace</p>
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
            placeholder="min 8 characters"
            required
            minLength={8}
          />

          {error && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full justify-center">
            Create account
          </Button>

          <p className="text-center text-xs text-[--text-muted]">
            Already registered?{" "}
            <Link href="/login" className="text-[--accent] hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
