"use client";

import React, { useState } from "react";
import { ImsAction, ItcAvailability, ReviewPacket } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import StatusBadge from "./StatusBadge";
import MatchStatusPill from "./MatchStatusPill";
import ActionDropdown from "./ActionDropdown";
import ItcIndicator from "./ItcIndicator";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PacketDetailProps {
  packet: ReviewPacket;
  onBack: () => void;

  currentAction?: ImsAction;
  onAction?: (action: ImsAction) => void;
  itcInfo?: { availability: string; claimPeriod?: string | null };
}

function RecordRow({
  record,
  highlighted,
}: {
  record: ReviewPacket["purchases"][number];
  highlighted?: boolean;
}) {
  return (
    <div
      className={`p-4 bg-secondary border rounded-md flex flex-wrap justify-between items-center gap-3 ${
        highlighted ? "border-l-4 border-l-primary border-border" : "border-border"
      }`}
    >
      <div className="flex flex-col gap-1 min-w-0">
        <span className="font-mono text-xs text-muted-foreground break-all">{record.record_id}</span>
        <span className="font-medium">
          {record.vendor_name || <span className="text-muted-foreground italic">Unknown Vendor</span>}
        </span>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm mt-1">
          <span className="text-muted-foreground">
            Ref: <span className="text-foreground font-mono">{record.reference || "N/A"}</span>
          </span>
          <span className="text-muted-foreground">
            GSTIN: <span className="text-foreground font-mono">{record.tax_identity || "N/A"}</span>
          </span>
          <span className="text-muted-foreground">
            Date: <span className="text-foreground">{record.record_date}</span>
          </span>
          {record.place_of_supply && (
            <span className="text-muted-foreground">
              POS: <span className="text-foreground font-mono">{record.place_of_supply}</span>
            </span>
          )}
          {record.is_reverse_charge && <Badge variant="warning">Reverse Charge</Badge>}
        </div>
        {(record.taxable_value || record.cgst || record.sgst || record.igst || record.cess) && (
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs font-mono text-muted-foreground mt-1">
            {record.taxable_value && <span>Taxable: {record.taxable_value}</span>}
            {record.cgst && <span>CGST: {record.cgst}</span>}
            {record.sgst && <span>SGST: {record.sgst}</span>}
            {record.igst && <span>IGST: {record.igst}</span>}
            {record.cess && <span>CESS: {record.cess}</span>}
          </div>
        )}
      </div>
      <div className="text-lg font-semibold font-mono whitespace-nowrap tabular-nums">
        ₹{parseFloat(record.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
      </div>
    </div>
  );
}

export default function PacketDetail({
  packet,
  onBack,

  currentAction,
  onAction,
  itcInfo,
}: PacketDetailProps) {
  const hyp = packet.competitors?.[0];
  const imsAction = currentAction ?? packet.ims?.action ?? "No Action";
  const itcAvailability =
    (itcInfo?.availability as ItcAvailability) ??
    (imsAction === "Accept" ? "Available" : "Unknown");

  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null);

  const handleFeedback = async (action: "Approve" | "Reject") => {
    try {
      const res = await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          packet_id: packet.packet_id,
          action,
          payload: { purchases: packet.purchases, gsts: packet.gsts, hypothesis: hyp },
        }),
      });
      if (res.ok) {
        setFeedbackStatus(`Successfully recorded: ${action}`);
        setTimeout(onBack, 1500);
      } else {
        setFeedbackStatus("Failed to record feedback.");
      }
    } catch (e) {
      console.error("Feedback error", e);
      setFeedbackStatus("Failed to record feedback.");
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-300">
      <div className="flex items-start gap-4 border-b border-border pb-4">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to review queue" className="mt-1">
          <svg aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </Button>
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-bold font-mono text-foreground">{packet.packet_id}</h2>
            <StatusBadge value={packet.action} kind="action" />
            {packet.match_status && <MatchStatusPill status={packet.match_status} />}
          </div>
          <p className="text-base text-muted-foreground mt-1">{packet.headline}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">

          {typeof packet.ml_confidence === "number" && (
            <div className="flex items-center gap-4 mr-4">
              <div className="flex flex-col items-end">
                <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Champion (LGBM)</span>
                <span className={`text-sm font-bold font-mono px-2 py-0.5 rounded mt-1 border ${
                  packet.ml_confidence >= 0.85 ? "bg-green-100 text-green-800 border-green-300" :
                  packet.ml_confidence >= 0.50 ? "bg-yellow-100 text-yellow-800 border-yellow-300" :
                  "bg-red-100 text-red-800 border-red-300"
                }`}>
                  {(packet.ml_confidence * 100).toFixed(1)}%
                </span>
              </div>
              {packet.ai_provenance && packet.ai_provenance.challenger_confidence !== undefined && (
                <div className="flex flex-col items-end border-l border-border pl-4">
                  <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1">
                    <svg className="w-3 h-3 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    Challenger
                  </span>
                  <span className="text-sm font-bold font-mono px-2 py-0.5 rounded mt-1 bg-secondary border border-border text-muted-foreground">
                    {(packet.ai_provenance.challenger_confidence * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          )}
          {feedbackStatus ? (
            <span className="text-sm text-success font-medium">{feedbackStatus}</span>
          ) : (
            <>
              <button
                onClick={() => handleFeedback("Reject")}
                className="px-4 py-2 rounded bg-transparent border border-destructive text-destructive hover:bg-destructive hover:text-white transition-colors text-sm font-semibold"
              >
                Reject as Contradiction
              </button>
              <button
                onClick={() => handleFeedback("Approve")}
                className="px-4 py-2 rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity text-sm font-semibold shadow-md"
              >
                Approve as Match
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: The Records */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <Card aria-labelledby="record-comparison-heading">
            <CardContent className="pt-1">
              <h3 id="record-comparison-heading" className="text-base font-semibold mb-4 flex items-center gap-2">
                <svg aria-hidden="true" className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Record Comparison
              </h3>

              <div className="mb-6">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Internal Purchases</h4>
                {packet.purchases.length === 0 ? (
                  <div className="p-4 bg-muted border border-border rounded text-sm text-muted-foreground">No purchase records in this packet.</div>
                ) : (
                  <div className="space-y-3">
                    {packet.purchases.map((p) => <RecordRow key={p.record_id} record={p} />)}
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Counterparty GST</h4>
                {packet.gsts.length === 0 ? (
                  <div className="p-4 bg-muted border border-border rounded text-sm text-muted-foreground">No GST records in this packet.</div>
                ) : (
                  <div className="space-y-3">
                    {packet.gsts.map((g) => <RecordRow key={g.record_id} record={g} highlighted />)}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Signals & Explanation */}
        <div className="flex flex-col gap-6">
          <Card aria-labelledby="semantic-findings-heading">
            <CardContent className="pt-1">
              <h3 id="semantic-findings-heading" className="text-base font-semibold mb-4 flex items-center gap-2">
                <svg aria-hidden="true" className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Semantic Findings
              </h3>

              <div className="space-y-4">
                {hyp?.violations?.length ? (
                  <ul className="flex flex-col gap-2" aria-label="Blocking semantic findings">
                    {hyp.violations.map((finding: string, i: number) => (
                      <li key={i} className="px-3 py-2 bg-destructive/15 text-destructive border border-destructive/40 rounded text-sm font-medium flex items-start gap-2">
                        <svg aria-hidden="true" className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {finding}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-3 bg-muted border border-border rounded text-sm text-muted-foreground text-center italic">No blocking semantic findings detected.</div>
                )}
              </div>

              <div className="mt-6 pt-6 border-t border-border">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI Legal & Contextual Explanation</h4>
                <div className="text-sm bg-secondary p-4 rounded border border-border leading-relaxed whitespace-pre-wrap">
                  {packet.llm_explanation ?? (
                    (() => {
                      const violations = hyp?.violations || [];
                      const diff = hyp?.supporting_evidence?.contributions?.amount?.metadata?.interpretation?.absolute_difference;
                      if (violations.length === 0 && !diff) {
                        return "AI Assessment: The records appear to match substantially with no major discrepancies found. The system recommends proceeding with the match.";
                      }
                      const parts = [];
                      if (diff && parseFloat(diff) !== 0) {
                        parts.push(`An absolute amount discrepancy of ₹${parseFloat(diff).toLocaleString("en-IN", { minimumFractionDigits: 2 })} was detected between the records.`);
                      }
                      if (violations.includes("SEVERE_AMOUNT_CONFLICT")) {
                        parts.push("This constitutes a severe amount conflict that exceeds acceptable tolerance thresholds.");
                      }
                      if (violations.includes("AMOUNT_MULTIPLE")) {
                        parts.push("The discrepancy suggests a multiple of the expected amount, potentially indicating a duplicated invoice, a consolidated entry, or a unit-of-measure mismatch.");
                      }
                      if (violations.includes("INVOICE_DATE_MISMATCH") || violations.includes("TEMPORAL_CONFLICT")) {
                        parts.push("The invoice dates or filing periods do not align between the purchase register and the counterparty GST records.");
                      }
                      return `AI Assessment: ${parts.join(" ")} Manual review is recommended to verify the source documentation before claiming ITC.`;
                    })()
                  )}
                </div>
                {packet.llm_citation && (
                  <div className="mt-3 p-3 bg-muted border border-border rounded text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground block mb-1">Citations & Retrieval Trace:</span>
                    <div className="font-mono whitespace-pre-wrap">{packet.llm_citation}</div>
                  </div>
                )}
              </div>

              <div className="mt-6 pt-6 border-t border-border">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Explanation Trajectory</h4>
                <div className="text-xs bg-muted p-4 rounded border border-border whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed overflow-x-auto max-h-96">
                  {packet.explanation ? JSON.stringify(packet.explanation, null, 2) : "Engine rationale is logged in the Trace."}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card aria-labelledby="ims-workflow-heading">
            <CardContent className="pt-1">
              <h3 id="ims-workflow-heading" className="text-base font-semibold mb-4 flex items-center gap-2">
                <svg aria-hidden="true" className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                IMS Decision
              </h3>
              <ActionDropdown current={imsAction} onAction={onAction} />
              <div className="mt-4">
                <ItcIndicator availability={itcAvailability} claimPeriod={itcInfo?.claimPeriod} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
