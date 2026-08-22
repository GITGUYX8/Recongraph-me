"use client";

import React, { useState } from "react";
import { ImsAction, ReviewPacket } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import StatusBadge from "./StatusBadge";

interface ReviewQueueProps {
  packets: ReviewPacket[];
  onSelectPacket: (packet: ReviewPacket) => void;
  imsActions?: Record<string, ImsAction>;
}

const FILTERS: { id: string; label: string }[] = [
  { id: "ALL", label: "All" },
  { id: "HIGH", label: "High Priority" },
  { id: "MEDIUM", label: "Medium Priority" },
  { id: "LOW", label: "Low Priority" },
];

const SORT_OPTIONS: { id: string; label: string }[] = [
  { id: "RISK", label: "Highest Risk First" },
  { id: "FINANCIAL", label: "Highest Financial Impact" },
  { id: "CONFIDENCE", label: "Lowest Match Confidence" },
  { id: "PRIORITY", label: "Priority" },
];

export default function ReviewQueue({ packets, onSelectPacket, imsActions }: ReviewQueueProps) {
  const [filter, setFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("RISK");

  const filteredPackets =
    filter === "ALL" ? packets : packets.filter((p) => p.risk_profile?.priority === filter);

  const sortedPackets = [...filteredPackets].sort((a, b) => {
    if (sortBy === "RISK") {
      return (b.risk_profile?.score || 0) - (a.risk_profile?.score || 0);
    } else if (sortBy === "FINANCIAL") {
      return (b.risk_profile?.financial_impact || 0) - (a.risk_profile?.financial_impact || 0);
    } else if (sortBy === "CONFIDENCE") {
      return (a.ml_confidence || 0) - (b.ml_confidence || 0);
    } else if (sortBy === "PRIORITY") {
      const pmap: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
      return (pmap[b.risk_profile?.priority || "LOW"] || 0) - (pmap[a.risk_profile?.priority || "LOW"] || 0);
    }
    return 0;
  });

  return (
    <Card className="gap-0 py-0" aria-labelledby="review-queue-heading">
      {/* Header & Filters */}
      <div className="px-4 py-3 border-b border-border flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="review-queue-heading" className="text-base font-semibold">
            Action Queue
          </h3>
          <p className="text-xs text-muted-foreground">
            {sortedPackets.length} packet{sortedPackets.length !== 1 ? "s" : ""} requiring human review or resolution
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex gap-1.5" role="group" aria-label="Filter packets by action">
            {FILTERS.map((f) => (
              <Button
                key={f.id}
                size="sm"
                variant={filter === f.id ? "secondary" : "ghost"}
                onClick={() => setFilter(f.id)}
                aria-pressed={filter === f.id}
              >
                {f.label}
              </Button>
            ))}
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sort:</span>
            <select
              className="text-sm bg-background border border-border rounded px-2 py-1 outline-none focus:ring-1 focus:ring-primary text-foreground"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="Sort packets"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse" aria-label="Review packets">
          <thead>
            <tr className="bg-secondary border-b border-border text-muted-foreground text-xs uppercase tracking-wider">
              <th scope="col" className="px-4 py-2.5 font-medium">Packet ID</th>
              <th scope="col" className="px-4 py-2.5 font-medium">Priority</th>
              <th scope="col" className="px-4 py-2.5 font-medium w-1/2">Headline</th>
              <th scope="col" className="px-4 py-2.5 font-medium">Shape (P:G)</th>
              <th scope="col" className="px-4 py-2.5 font-medium">IMS</th>
              <th scope="col" className="px-4 py-2.5 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {sortedPackets.map((pkt) => {
              const imsAction = imsActions?.[pkt.packet_id] ?? pkt.ims?.action ?? "No Action";

              return (
                <tr
                  key={pkt.packet_id}
                  tabIndex={0}
                  role="button"
                  aria-label={`Open review packet ${pkt.packet_id}`}
                  className="border-b border-border hover:bg-muted transition-colors cursor-pointer"
                  onClick={() => onSelectPacket(pkt)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectPacket(pkt);
                    }
                  }}
                >
                  <td className="px-4 py-3 font-mono text-sm">{pkt.packet_id}</td>
                  <td className="px-4 py-3">
                    {pkt.risk_profile ? (
                      <div className="flex flex-col gap-1 items-start">
                        <Badge variant={pkt.risk_profile.priority === "HIGH" ? "danger" : pkt.risk_profile.priority === "MEDIUM" ? "warning" : "success"} className="text-[10px]">
                          {pkt.risk_profile.priority}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground font-mono">Score: {pkt.risk_profile.score}</span>
                      </div>
                    ) : (
                      <StatusBadge value={pkt.action} kind="action" />
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm block truncate max-w-md" title={pkt.headline}>
                      {pkt.headline}
                    </span>
                    {pkt.llm_explanation && (
                      <div className="mt-1">
                        <p className="text-xs text-[var(--color-primary)] truncate max-w-md italic" title={pkt.llm_explanation}>
                          ✨ AI: {pkt.llm_explanation}
                        </p>
                        {pkt.llm_citation && (
                          <div className="mt-2 p-2 bg-[var(--color-surface-elevated)] border-l-2 border-[var(--color-primary)] rounded text-[10px] text-[var(--color-text-muted)] line-clamp-2" title={pkt.llm_citation}>
                            <span className="font-semibold text-xs mb-1 block">🏛️ Grounding Law:</span>
                            {pkt.llm_citation}
                          </div>
                        )}
                      </div>
                    )}
                    {pkt.risk_profile && pkt.risk_profile.reasons.length > 0 && (
                      <div className="mt-2 text-xs">
                        <span className="font-medium text-muted-foreground block mb-0.5">
                          Why this is {(pkt.risk_profile.priority || "LOW").toLowerCase()} priority:
                        </span>
                        <ul className="list-disc list-inside text-muted-foreground/80 space-y-0.5">
                          {pkt.risk_profile.reasons.map((r, idx) => (
                            <li key={idx} className="truncate max-w-md" title={r}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </td>
                  <td className="p-4 text-sm font-medium">
                    {pkt.ml_confidence !== null && pkt.ml_confidence !== undefined ? 
                      <span className={`px-2 py-0.5 rounded text-xs ${(pkt.ml_confidence > 0.8) ? 'bg-[var(--color-success-muted)] text-[var(--color-success)] border border-[var(--color-success)]/30' : 'bg-[var(--color-surface-elevated)] text-[var(--color-text-muted)] border border-[var(--color-border)]'}`}>
                        {(pkt.ml_confidence * 100).toFixed(1)}%
                      </span> 
                    : <span className="text-[var(--color-text-muted)] opacity-50">-</span>}
                  </td>
                  <td className="px-4 py-3 text-sm font-mono text-muted-foreground">
                    {pkt.purchases.length}:{pkt.gsts.length}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge value={imsAction} kind="ims" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-primary text-sm font-medium">
                      Open Review <span aria-hidden="true">→</span>
                    </span>
                  </td>
                </tr>
              );
            })}

            {sortedPackets.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-muted-foreground">
                  No packets match the selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
