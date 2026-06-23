// Detect if running inside a Tauri desktop window.
export const isTauri = (): boolean =>
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

// Lazy-load Tauri invoke only when in the desktop context.
async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) throw new Error("not running in Tauri");
  const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
  return tauriInvoke<T>(cmd, args);
}

export type BackendStatus = "running" | "stopped" | string;

export const tauriBackend = {
  start: () => invoke<string>("start_backend"),
  stop: () => invoke<string>("stop_backend"),
  status: () => invoke<string>("backend_status"),
};

export interface DatabaseInfo {
  path: string;
  exists: boolean;
  size_bytes: number;
  size_mb: number;
}

export const tauriDatabase = {
  info: () => invoke<DatabaseInfo>("database_info"),
  export: (destPath: string) => invoke<string>("export_database", { destPath }),
  import: (srcPath: string) => invoke<string>("import_database", { srcPath }),
};
