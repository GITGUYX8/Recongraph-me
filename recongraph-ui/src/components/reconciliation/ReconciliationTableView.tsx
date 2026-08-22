"use client";

import React, { useMemo, useState } from "react";
import {
  ReconciliationResult,
  ReviewPacket,
  RecordData,
  ActionType,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type BadgeVariant = "warning" | "info" | "danger" | "neutral" | "success";

const ACTION_META: Record<
  ActionType,
  { label: string; variant: BadgeVariant }
> = {
  auto_match: { label: "Matched", variant: "success" },
  review_ambiguous: { label: "Ambiguous", variant: "warning" },
  review_weak: { label: "Weak Evidence", variant: "info" },
  no_match: { label: "Unmatched", variant: "danger" },
};

const TABS = [
  { id: "summary", label: "Summary" },
  { id: "suppliers", label: "Suppliers" },
  { id: "invoices", label: "Invoices" },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface ReconciliationTableViewProps {
  result: ReconciliationResult;
  onSelectPacket: (packet: ReviewPacket) => void;
}

function fmtAmount(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtSignedDiff(purchase?: RecordData, gst?: RecordData): string {
  if (!purchase || !gst) return "—";
  const diff = parseFloat(gst.amount) - parseFloat(purchase.amount);
  const sign = diff > 0 ? "+" : diff < 0 ? "−" : "";
  return `${sign}${fmtAmount(Math.abs(diff))}`;
}

interface InvoiceRow {
  packet: ReviewPacket;
  purchase?: RecordData;
  gst?: RecordData;
}

interface SupplierGroup {
  key: string;
  name: string;
  gstin: string;
  purchaseCount: number;
  gstCount: number;
  totalDiff: number;
  worstAction: ActionType;
}

const SEVERITY_ORDER: ActionType[] = [
  "no_match",
  "review_ambiguous",
  "review_weak",
  "auto_match",
];

export default function ReconciliationTableView({
  result,
  onSelectPacket,
}: ReconciliationTableViewProps) {
  const [tab, setTab] = useState<TabId>("invoices");

  const invoiceRows = useMemo<InvoiceRow[]>(() => {
    const rows: InvoiceRow[] = [];
    for (const pkt of result.review_packets) {
      const maxLen = Math.max(pkt.purchases.length, pkt.gsts.length, 1);
      for (let i = 0; i < maxLen; i++) {
        rows.push({ packet: pkt, purchase: pkt.purchases[i], gst: pkt.gsts[i] });
      }
    }
    return rows;
  }, [result.review_packets]);

  const summaryRows = useMemo(() => {
    const byAction = new Map<ActionType, { p: number; g: number; diff: number }>();
    result.auto_matches.forEach(() => {
      const entry = byAction.get("auto_match") ?? { p: 0, g: 0, diff: 0 };
      entry.p += 1;
      entry.g += 1;
      byAction.set("auto_match", entry);
    });
    for (const pkt of result.review_packets) {
      const entry = byAction.get(pkt.action) ?? { p: 0, g: 0, diff: 0 };
      entry.p += pkt.purchases.length;
      entry.g += pkt.gsts.length;
      if (pkt.purchases[0] && pkt.gsts[0]) {
        entry.diff += Math.abs(
          parseFloat(pkt.gsts[0].amount) - parseFloat(pkt.purchases[0].amount)
        );
      }
      byAction.set(pkt.action, entry);
    }
    return SEVERITY_ORDER.filter((a) => byAction.has(a)).map((action) => ({
      action,
      ...byAction.get(action)!,
    }));
  }, [result]);

  const supplierGroups = useMemo<SupplierGroup[]>(() => {
    const groups = new Map<string, SupplierGroup>();
    for (const pkt of result.review_packets) {
      const lead = pkt.purchases[0] ?? pkt.gsts[0];
      if (!lead) continue;
      const key = lead.tax_identity || lead.vendor_name || lead.record_id;
      const group =
        groups.get(key) ??
        ({
          key,
          name: lead.vendor_name || "Unknown Vendor",
          gstin: lead.tax_identity || "—",
          purchaseCount: 0,
          gstCount: 0,
          totalDiff: 0,
          worstAction: "auto_match",
        } satisfies SupplierGroup);
      group.purchaseCount += pkt.purchases.length;
      group.gstCount += pkt.gsts.length;
      if (pkt.purchases[0] && pkt.gsts[0]) {
        group.totalDiff += Math.abs(
          parseFloat(pkt.gsts[0].amount) - parseFloat(pkt.purchases[0].amount)
        );
      }
      if (
        SEVERITY_ORDER.indexOf(pkt.action) <
        SEVERITY_ORDER.indexOf(group.worstAction)
      ) {
        group.worstAction = pkt.action;
      }
      groups.set(key, group);
    }
    return [...groups.values()].sort((a, b) => b.totalDiff - a.totalDiff);
  }, [result.review_packets]);

  const thBase =
    "px-3 py-2 text-xs font-medium uppercase tracking-wider border-b border-border first:pl-4 last:pr-4";

  return (
    <Card className="gap-0 py-0 overflow-hidden">
      {/* Tab bar */}
      <div className="px-4 py-3 border-b border-border flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">Reconciliation Sheet</h3>
          <p className="text-xs text-muted-foreground">
            Excel-style ledger view of engine results
          </p>
        </div>
        <div className="flex gap-1.5" role="group" aria-label="Switch sheet view">
          {TABS.map((t) => (
            <Button
              key={t.id}
              size="sm"
              variant={tab === t.id ? "secondary" : "ghost"}
              onClick={() => setTab(t.id)}
              aria-pressed={tab === t.id}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </div>

      {tab === "summary" && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse" aria-label="Match summary">
            <caption className="sr-only">Match summary by status</caption>
            <thead>
              <tr className="bg-secondary text-muted-foreground">
                <th scope="col" className={thBase}>Match Status</th>
                <th scope="col" className={`${thBase} text-right`}>Purchase Docs</th>
                <th scope="col" className={`${thBase} text-right`}>GSTR Docs</th>
                <th scope="col" className={`${thBase} text-right bg-destructive/10`}>
                  Amount Diff (₹)
                </th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {summaryRows.map((row) => {
                const meta = ACTION_META[row.action];
                return (
                  <tr key={row.action} className="border-b border-border/50 hover:bg-muted/40">
                    <td className="px-3 py-3 first:pl-4">
                      <Badge variant={meta.variant}>{meta.label}</Badge>
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono">{row.p}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono">{row.g}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono bg-destructive/10 last:pr-4">
                      {fmtAmount(row.diff)}
                    </td>
                  </tr>
                );
              })}
              {summaryRows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-muted-foreground">
                    No data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "suppliers" && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse" aria-label="Supplier summary">
            <caption className="sr-only">Supplier summary</caption>
            <thead>
              <tr className="bg-secondary text-muted-foreground">
                <th scope="col" className={thBase}>Supplier</th>
                <th scope="col" className={thBase}>GSTIN</th>
                <th scope="col" className={`${thBase} text-right`}>Purchases</th>
                <th scope="col" className={`${thBase} text-right`}>GSTR</th>
                <th scope="col" className={`${thBase} text-right bg-destructive/10`}>
                  Total Diff (₹)
                </th>
                <th scope="col" className={thBase}>Severity</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {supplierGroups.map((g) => {
                const meta = ACTION_META[g.worstAction];
                return (
                  <tr key={g.key} className="border-b border-border/50 hover:bg-muted/40">
                    <td className="px-3 py-3 font-medium first:pl-4">{g.name}</td>
                    <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{g.gstin}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono">{g.purchaseCount}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono">{g.gstCount}</td>
                    <td className="px-3 py-3 text-right tabular-nums font-mono bg-destructive/10">
                      {fmtAmount(g.totalDiff)}
                    </td>
                    <td className="px-3 py-3 last:pr-4">
                      <Badge variant={meta.variant}>{meta.label}</Badge>
                    </td>
                  </tr>
                );
              })}
              {supplierGroups.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-muted-foreground">
                    No suppliers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "invoices" && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm" aria-label="Invoice detail comparison">
            <caption className="sr-only">
              Side-by-side purchase register vs GSTR-2B comparison
            </caption>
            <thead>
              <tr className="text-xs uppercase tracking-wider">
                <th scope="col" rowSpan={2} className={`${thBase} align-bottom bg-secondary`}>
                  Packet
                </th>
                <th scope="col" colSpan={4} className={`text-center border-b border-border bg-success/15 text-success`}>
                  Purchase Register
                </th>
                <th scope="col" colSpan={4} className={`text-center border-b border-border bg-info/15 text-info`}>
                  GSTR-2B
                </th>
                <th scope="col" colSpan={3} className={`text-center border-b border-border bg-destructive/10 text-destructive`}>
                  Differences & Risk
                </th>
              </tr>
              <tr className="bg-secondary text-muted-foreground">
                <th scope="col" className={thBase}>Bill No</th>
                <th scope="col" className={thBase}>Date</th>
                <th scope="col" className={thBase}>GSTIN</th>
                <th scope="col" className={`${thBase} text-right`}>Amount</th>
                <th scope="col" className={thBase}>Bill No</th>
                <th scope="col" className={thBase}>Date</th>
                <th scope="col" className={thBase}>GSTIN</th>
                <th scope="col" className={`${thBase} text-right`}>Amount</th>
                <th scope="col" className={`${thBase} text-right`}>Δ Amount (₹)</th>
                <th scope="col" className={`${thBase} text-center`}>Flags</th>
                <th scope="col" className={`${thBase} text-center last:pr-4`}>Priority</th>
              </tr>
            </thead>
            <tbody>
              {invoiceRows.map((row, i) => {
                const meta = ACTION_META[row.packet.action];
                const findings = row.packet.competitors?.[0]?.violations ?? [];
                const cellSide = (side: "purchase" | "gst") =>
                  side === "purchase"
                    ? "bg-success/8 border-l border-success/20"
                    : "bg-info/8 border-l border-info/20";

                return (
                  <tr
                    key={`${row.packet.packet_id}-${i}`}
                    tabIndex={0}
                    role="button"
                    aria-label={`Open review packet ${row.packet.packet_id}`}
                    className="border-b border-border/50 hover:bg-muted/40 cursor-pointer transition-colors"
                    onClick={() => onSelectPacket(row.packet)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectPacket(row.packet);
                      }
                    }}
                  >
                    <td className="px-3 py-2.5 pl-4 whitespace-nowrap">
                      <span className="font-mono text-xs text-muted-foreground block">
                        {row.packet.packet_id}
                      </span>
                      <Badge variant={meta.variant} className="mt-0.5">
                        {meta.label}
                      </Badge>
                    </td>

                    <td className={`px-3 py-2.5 font-mono text-xs ${cellSide("purchase")}`}>
                      {row.purchase?.reference ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 text-xs ${cellSide("purchase")}`}>
                      {row.purchase?.record_date ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 font-mono text-xs ${cellSide("purchase")}`}>
                      {row.purchase?.tax_identity ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 text-right tabular-nums font-medium ${cellSide("purchase")}`}>
                      {row.purchase ? fmtAmount(row.purchase.amount) : "—"}
                    </td>

                    <td className={`px-3 py-2.5 font-mono text-xs ${cellSide("gst")}`}>
                      {row.gst?.reference ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 text-xs ${cellSide("gst")}`}>
                      {row.gst?.record_date ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 font-mono text-xs ${cellSide("gst")}`}>
                      {row.gst?.tax_identity ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className={`px-3 py-2.5 text-right tabular-nums font-medium ${cellSide("gst")}`}>
                      {row.gst ? fmtAmount(row.gst.amount) : "—"}
                    </td>

                    <td className="px-3 py-2.5 text-right tabular-nums font-mono bg-destructive/10">
                      {fmtSignedDiff(row.purchase, row.gst)}
                    </td>
                    <td className="px-3 py-2.5 text-center pr-4 bg-destructive/10">
                      {findings.length > 0 ? (
                        <span
                          className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-destructive/20 text-destructive"
                          title={findings.join(", ")}
                        >
                          {findings.length}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-center pr-4">
                      {row.packet.risk_profile ? (
                        <Badge variant={row.packet.risk_profile.priority === "HIGH" ? "danger" : row.packet.risk_profile.priority === "MEDIUM" ? "warning" : "success"} className="text-[10px]">
                          {row.packet.risk_profile.priority}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {invoiceRows.length === 0 && (
                <tr>
                  <td colSpan={12} className="px-4 py-10 text-center text-muted-foreground">
                    No invoices match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
