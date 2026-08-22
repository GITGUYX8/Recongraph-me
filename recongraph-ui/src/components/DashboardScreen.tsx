"use client";

import React, { useState, useMemo } from "react";
import { ImsAction, ReconciliationResult, ReviewPacket } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import ReviewQueue from "./ReviewQueue";
import PacketDetail from "./PacketDetail";
import ReconciliationTableView from "./reconciliation/ReconciliationTableView";
import ExportButton from "./ExportButton";
import { applyImsAction } from "@/lib/api";

interface DashboardScreenProps {
  result: ReconciliationResult;
  runId?: string | null;
}

interface ItcInfo {
  availability: string;
  claimPeriod?: string | null;
}



type ViewMode = "sheet" | "queue";

export default function DashboardScreen({ result, runId }: DashboardScreenProps) {
  const [selectedPacket, setSelectedPacket] = useState<ReviewPacket | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("sheet");
  const [imsActions, setImsActions] = useState<Record<string, ImsAction>>({});
  const [imsItc, setImsItc] = useState<Record<string, ItcInfo>>({});

  async function handleImsAction(packetId: string, action: ImsAction) {
    setImsActions((prev) => ({ ...prev, [packetId]: action }));

    if (!runId) return; // static demo — local-only

    try {
      const applied = await applyImsAction(runId, packetId, action);
      setImsItc((prev) => ({
        ...prev,
        [packetId]: {
          availability: applied.itc_availability ?? "Unknown",
          claimPeriod: applied.itc_claim_period,
        },
      }));
    } catch (e) {
      console.warn("Action API call failed; keeping local state", e);
    }
  }

  const augmentedResult = useMemo(() => {
    return {
      ...result,
      review_packets: [...(result.review_packets || [])].sort((a, b) => (b.risk_profile?.score || 0) - (a.risk_profile?.score || 0)) // Highest Risk First
    };
  }, [result]);

  const prioritySummary = useMemo(() => {
    const summary = {
      HIGH: { count: 0, impact: 0 },
      MEDIUM: { count: 0, impact: 0 },
      LOW: { count: 0, impact: 0 },
    };
    augmentedResult.review_packets?.forEach(pkt => {
      const p = pkt.risk_profile?.priority || "LOW";
      if (summary[p]) {
        summary[p].count += 1;
        summary[p].impact += pkt.risk_profile?.financial_impact || 0;
      }
    });
    return summary;
  }, [augmentedResult]);

  // Derive stats
  const totalAuto = augmentedResult.auto_matches?.length || 0;
  const totalReview = augmentedResult.review_packets?.length || 0;

  // Conservation check: count unique record IDs across outputs
  const outPurchaseIds = new Set<string>();
  const outGstIds = new Set<string>();

  augmentedResult.auto_matches?.forEach((d) => {
    d.selected_hypothesis?.hypothesis_identity?.forEach((edge) => {
      outPurchaseIds.add(edge[0].split(":").pop()!);
      outGstIds.add(edge[1].split(":").pop()!);
    });
  });

  augmentedResult.review_packets?.forEach((pkt) => {
    pkt.purchases?.forEach((p) => outPurchaseIds.add(p.record_id));
    pkt.gsts?.forEach((g) => outGstIds.add(g.record_id));
  });

  const totalIn = outPurchaseIds.size + outGstIds.size;
  const matchRate = totalIn > 0 ? (((totalAuto * 2) / totalIn) * 100).toFixed(1) : "0.0";

  if (selectedPacket) {
    return (
      <PacketDetail
        packet={selectedPacket}
        onBack={() => setSelectedPacket(null)}

        currentAction={imsActions[selectedPacket.packet_id]}
        onAction={(action) => handleImsAction(selectedPacket.packet_id, action)}
        itcInfo={imsItc[selectedPacket.packet_id]}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-300">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card size="sm">
          <CardContent>
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Records Processed
            </span>
            <span className="text-2xl font-bold mt-1 block tabular-nums">{totalIn}</span>
          </CardContent>
        </Card>

        <Card size="sm" className="border-l-4 border-l-success">
          <CardContent>
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Auto-Matched
            </span>
            <span className="text-2xl font-bold mt-1 block tabular-nums text-success">{totalAuto}</span>
            <span className="text-xs text-success mt-0.5 block">{matchRate}% match rate</span>
          </CardContent>
        </Card>

        <Card size="sm" className="border-l-4 border-l-warning">
          <CardContent>
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              In Review
            </span>
            <span className="text-2xl font-bold mt-1 block tabular-nums text-warning">{totalReview}</span>
            <span className="text-xs text-warning mt-0.5 block">Requires attention</span>
          </CardContent>
        </Card>

        {/* Conservation Indicator */}
        <Card size="sm" className="bg-accent ring-accent-foreground/20">
          <CardContent>
            <div className="flex items-center gap-2">
              <svg aria-hidden="true" className="w-4 h-4 text-accent-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span className="text-xs font-medium uppercase tracking-wider text-accent-foreground">
                Strict Conservation
              </span>
            </div>
            <span className="text-sm font-semibold mt-1 block text-accent-foreground">Records In = Records Out</span>
            <span className="text-xs text-accent-foreground/80">Zero data loss guaranteed</span>
          </CardContent>
        </Card>
      </div>

      {/* Priority Summary */}
      <Card className="bg-muted/30 border-muted">
        <CardContent className="py-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Reconciliation Priority Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1 p-3 rounded border border-destructive/20 bg-destructive/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-destructive uppercase">High Priority</span>
                <Badge variant="danger" className="text-xs">{prioritySummary.HIGH.count}</Badge>
              </div>
              <span className="text-xs text-muted-foreground mt-1">Critical Risk - Investigate Immediately</span>
              <span className="text-sm font-mono font-medium mt-1">Financial Impact: ₹{prioritySummary.HIGH.impact.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
            </div>
            
            <div className="flex flex-col gap-1 p-3 rounded border border-warning/30 bg-warning/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-warning-foreground uppercase">Medium Priority</span>
                <Badge variant="warning" className="text-xs">{prioritySummary.MEDIUM.count}</Badge>
              </div>
              <span className="text-xs text-muted-foreground mt-1">Needs Review</span>
              <span className="text-sm font-mono font-medium mt-1">Financial Impact: ₹{prioritySummary.MEDIUM.impact.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
            </div>

            <div className="flex flex-col gap-1 p-3 rounded border border-success/30 bg-success/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-success uppercase">Low Priority</span>
                <Badge variant="success" className="text-xs">{prioritySummary.LOW.count}</Badge>
              </div>
              <span className="text-xs text-muted-foreground mt-1">Minor Issues / Monitor</span>
              <span className="text-sm font-mono font-medium mt-1">Financial Impact: ₹{prioritySummary.LOW.impact.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2 items-center justify-between">
        <div className="flex gap-2 items-center">
          <Badge variant="neutral">Engine: {augmentedResult.engine_version}</Badge>
          <Badge variant="neutral" className="font-mono normal-case max-w-xs truncate" >
            Config: {augmentedResult.traces?.[0]?.config_hash}
          </Badge>
          <Badge variant={runId ? "success" : "warning"}>
            {runId ? "Backend run" : "Static demo"}
          </Badge>
        </div>

        <div className="flex gap-1.5 flex-wrap" role="group" aria-label="Switch results view">
          <Button
            size="sm"
            variant={viewMode === "sheet" ? "secondary" : "ghost"}
            onClick={() => setViewMode("sheet")}
            aria-pressed={viewMode === "sheet"}
          >
            Sheet View
          </Button>
          <Button
            size="sm"
            variant={viewMode === "queue" ? "secondary" : "ghost"}
            onClick={() => setViewMode("queue")}
            aria-pressed={viewMode === "queue"}
          >
            Queue View
          </Button>
          <ExportButton result={augmentedResult} runId={runId} report="match_summary" />
          <ExportButton result={augmentedResult} runId={runId} report="supplier" />
          <ExportButton result={augmentedResult} runId={runId} report="invoice" />
        </div>
      </div>

      {viewMode === "sheet" ? (
        <ReconciliationTableView
          result={augmentedResult}
          onSelectPacket={setSelectedPacket}
        />
      ) : (
        <ReviewQueue
          packets={augmentedResult.review_packets}
          onSelectPacket={setSelectedPacket}
          imsActions={imsActions}
        />
      )}

    </div>
  );
}
