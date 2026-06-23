"use client";

export function setToken(token: string) {
  localStorage.setItem("apex_token", token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("apex_token");
}

export function clearToken() {
  localStorage.removeItem("apex_token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
