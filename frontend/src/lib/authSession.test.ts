import { describe, expect, it } from "vitest";

/** Mirrors cookie-auth expectations used by App.tsx and api.ts interceptors. */
function shouldAttemptRefresh(url: string, status: number, isRetry: boolean): boolean {
  const authPaths = ["/auth/login", "/auth/refresh", "/auth/signup-tenant", "/auth/signup-status", "/auth/logout"];
  if (status !== 401 || isRetry) return false;
  return !authPaths.some((p) => url.includes(p));
}

describe("auth session refresh policy", () => {
  it("retries protected API calls after 401", () => {
    expect(shouldAttemptRefresh("/api/v1/governance/runs", 401, false)).toBe(true);
  });

  it("does not retry login or refresh endpoints", () => {
    expect(shouldAttemptRefresh("/api/v1/auth/login", 401, false)).toBe(false);
    expect(shouldAttemptRefresh("/api/v1/auth/refresh", 401, false)).toBe(false);
  });

  it("does not loop on already-retried requests", () => {
    expect(shouldAttemptRefresh("/api/v1/governance/runs", 401, true)).toBe(false);
  });
});
