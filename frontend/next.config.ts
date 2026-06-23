import type { NextConfig } from "next";

const isTauriBuild = process.env.TAURI_ENV_TARGET_TRIPLE !== undefined;

const nextConfig: NextConfig = {
  // Static export for Tauri desktop builds; SSR mode for web deployments.
  output: isTauriBuild ? "export" : undefined,
  // Disable image optimization for static export (Tauri doesn't run a Next server).
  images: isTauriBuild ? { unoptimized: true } : undefined,
};

export default nextConfig;
