import type { ImsAction, ReconciliationResult } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const AUTH_TOKEN_KEY = "recongraph_access_token";

export class ApiAuthError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "ApiAuthError";
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.sessionStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

export async function login(username: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unable to sign in");
  }

  const data = (await res.json()) as { access_token?: string };
  if (!data.access_token) throw new Error("Authentication response was invalid");
  setAccessToken(data.access_token);
}

export async function signup(username: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unable to create account");
  }
}

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface DemoResponse {
  run_id: string;
  status: string;
  result: ReconciliationResult;
}

export interface AppliedAction {
  packet_id: string;
  action: string;
  status: string;
  itc_availability?: string;
  itc_claim_period?: string | null;
  reason_itc_unavailability?: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    clearAccessToken();
    window.dispatchEvent(new Event("recongraph:auth-required"));
    throw new ApiAuthError();
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

/** Load the demo (persisted as a run on the backend). */
export async function loadDemo(): Promise<DemoResponse> {
  return request<DemoResponse>("/demo");
}

/** Upload actual PR and GST files to the engine. */
export async function uploadFiles(purchases: File, gsts: File): Promise<DemoResponse> {
  const formData = new FormData();
  formData.append("purchases", purchases);
  formData.append("gsts", gsts);

  const res = await fetch(`${API_BASE}/reconcile`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (res.status === 401) {
    clearAccessToken();
    window.dispatchEvent(new Event("recongraph:auth-required"));
    throw new ApiAuthError();
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API /reconcile failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<DemoResponse>;
}

/** Poll the run status until success or failure. */
export async function pollRun(runId: string, maxAttempts = 600, intervalMs = 2000): Promise<DemoResponse> {
  for (let i = 0; i < maxAttempts; i++) {
    const data = await request<DemoResponse>(`/runs/${runId}`);
    if (data.status === "success" || data.status === "failed") {
      return data;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Polling timed out");
}


/** Apply an IMS action to a packet within a run. */
export async function applyImsAction(
  runId: string,
  packetId: string,
  action: ImsAction,
  reviewerId = "ui",
  comments = "",
): Promise<AppliedAction> {
  const body = {
    packets: [
      { packet_id: packetId, action, reviewer_id: reviewerId, comments },
    ],
  };
  const res = await request<{ applied: AppliedAction[] }>(
    `/runs/${runId}/actions`,
    { method: "POST", body: JSON.stringify(body) },
  );
  return res.applied[0];
}

/** Download a report from the backend and trigger a browser download. */
export async function exportReport(
  runId: string,
  report: "match_summary" | "supplier" | "invoice",
  format: "csv" | "xlsx" = "csv",
  filename?: string,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/runs/${runId}/export?report=${report}&format=${format}`,
    { headers: authHeaders() },
  );
  if (res.status === 401) {
    clearAccessToken();
    window.dispatchEvent(new Event("recongraph:auth-required"));
    throw new ApiAuthError();
  }
  if (!res.ok) {
    throw new Error(`Export failed (${res.status})`);
  }
  const blob = await res.blob();
  triggerDownload(blob, filename ?? `recongraph-${report}.${format}`);
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
