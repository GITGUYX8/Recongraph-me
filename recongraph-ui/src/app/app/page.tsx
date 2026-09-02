"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ReconciliationResult } from "@/lib/types";
import { Button } from "@/components/ui/button";

import UploadScreen from "@/components/UploadScreen";
import DashboardScreen from "@/components/DashboardScreen";
import AuthScreen from "@/components/AuthScreen";
import { ApiAuthError, clearAccessToken, getAccessToken, loadDemo, uploadFiles, pollRun } from "@/lib/api";

export default function AppPage() {
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    setIsAuthenticated(Boolean(getAccessToken()));

    const handleAuthRequired = () => {
      setIsAuthenticated(false);
      setResult(null);
      setRunId(null);
      setError("Your session expired. Please sign in again.");
    };
    window.addEventListener("recongraph:auth-required", handleAuthRequired);
    return () => window.removeEventListener("recongraph:auth-required", handleAuthRequired);
  }, []);

  const handleUpload = async (prFile: File, gstFile: File) => {
    setIsLoading(true);
    setError(null);
    try {
      const initResponse = await uploadFiles(prFile, gstFile);
      if (initResponse.run_id) {
        setRunId(initResponse.run_id);
        const finalResponse = await pollRun(initResponse.run_id);
        if (finalResponse.status === "success" && finalResponse.result) {
          setResult(finalResponse.result);
        } else {
          setError(`Run failed: ${finalResponse.message || "Unknown error"}`);
        }
      } else {
        setError("Failed to queue the reconciliation job.");
      }
    } catch (err) {
      console.error("Error uploading files:", err);
      setError(err instanceof ApiAuthError ? "Your session expired. Please sign in again." : "Failed to upload and process files. Check the console for details.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLoad = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Try backend first (FastAPI) — returns { run_id, result }
      try {
        const data = await loadDemo();
        if (data?.result) {
          setRunId(data.run_id ?? null);
          setResult(data.result);
          return;
        }
      } catch (e) {
        if (e instanceof ApiAuthError) throw e;
        console.warn("Backend /demo failed, falling back to static JSON", e);
      }

      // 2. Fallback to static JSON for instant load (no run_id)
      const res = await fetch("/demo_results.json");
      if (!res.ok) throw new Error("Failed to load static demo data");
      const data = await res.json();
      setRunId(null);
      setResult(data);
    } catch (err) {
      console.error("Error loading demo:", err);
      setError(err instanceof ApiAuthError ? "Your session expired. Please sign in again." : "Failed to load the demo dataset. Check the console for details.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthenticated === null) {
    return <main className="min-h-screen" aria-busy="true" />;
  }

  if (!isAuthenticated) {
    return <AuthScreen onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  const logout = () => {
    clearAccessToken();
    setIsAuthenticated(false);
    setResult(null);
    setRunId(null);
  };

  const reset = () => {
    setResult(null);
    setRunId(null);
  };

  return (
    <main className="min-h-screen px-4 py-6 md:px-6 max-w-7xl mx-auto flex flex-col gap-6">
      <header className="flex items-center justify-between border-b border-border pb-4">
        <Link href="/" className="group">
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Recon<span className="text-primary">Graph</span>
          </h1>
          <p className="text-muted-foreground text-xs mt-0.5 group-hover:text-foreground/80 transition-colors">
            Deterministic GST Reconciliation
          </p>
        </Link>

          <div className="flex items-center gap-2">
            {result && (
              <Button variant="outline" size="sm" onClick={reset}>
                Start New Run
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
      </header>

      {error && (
        <div
          role="alert"
          className="px-4 py-3 rounded-md bg-destructive/15 border border-destructive/40 text-destructive text-sm"
        >
          {error}
        </div>
      )}

      {!result ? (
        <UploadScreen onDemoLoad={handleDemoLoad} onUpload={handleUpload} isLoading={isLoading} />
      ) : (
        <DashboardScreen result={result} runId={runId} />
      )}
    </main>
  );
}
