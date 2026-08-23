import type { ImsAction, ReconciliationResult } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
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
    body: formData,
  });

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
  );
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
