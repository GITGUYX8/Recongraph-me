export type ActionType = "auto_match" | "review_weak" | "review_ambiguous" | "no_match";

export type ImsAction = "No Action" | "Accept" | "Reject" | "Pending" | "Ignore";

export type ItcAvailability = "Available" | "Unavailable" | "Ineligible" | "Unknown";

export type PriorityLevel = "HIGH" | "MEDIUM" | "LOW";

export interface RiskProfile {
  priority: PriorityLevel;
  score: number;
  reasons: string[];
  financial_impact: number;
}

export type MatchStatus =
  | "Exact Match"
  | "Suggested Match"
  | "Mismatch"
  | "Manual Match"
  | "Only in 2A/2B"
  | "Only in Books";

export interface RecordData {
  record_id: string;
  vendor_name: string | null;
  reference: string | null;
  amount: string;
  record_date: string;
  tax_identity: string | null;
  place_of_supply?: string | null;
  is_reverse_charge?: boolean | null;
  document_type?: string | null;
  is_return?: boolean | null;
  amendment_type?: string | null;
  fiscal_year?: string | null;
  company_gstin?: string | null;
  taxable_value?: string | null;
  cgst?: string | null;
  sgst?: string | null;
  igst?: string | null;
  cess?: string | null;
  irn_number?: string | null;
  irn_source?: string | null;
  classification?: string | null;
}

export interface EvaluatedHypothesis {
  hypothesis_identity: string[][];
  eligibility: string;
  violations: string[];
  base_score: number | null; // e.g. 10000 for 1.0, to be divided by 10000
  coverage: number | null;
  relationship_score: number | null;
  provider_projection_identities: string[];
}

export interface ExplanationNode {
  type: string;
  text: string;
  children: ExplanationNode[];
}

export interface ImsDecision {
  packet_id: string;
  action: ImsAction;
  status: string;
  reviewer_id?: string;
  comments?: string;
  updated_at?: string;
  itc_availability?: ItcAvailability;
  itc_claim_period?: string | null;
  reason_itc_unavailability?: string | null;
}

export interface ReviewPacket {
  packet_id: string;
  action: ActionType;
  headline: string;
  purchases: RecordData[];
  gsts: RecordData[];
  explanation: ExplanationNode | null;
  competitors: any[];
  ml_confidence?: number | null;
  llm_explanation?: string | null;
  llm_citation?: string | null;
  ai_provenance?: any;
  ims?: ImsDecision | null;
  match_status?: MatchStatus;
  risk_profile?: RiskProfile;
}

export interface AutoMatch {
  action: ActionType;
  selected_hypothesis: EvaluatedHypothesis;
  rationale: string;
}

export interface DecisionTrace {
  trace_id: string;
  engine_version: string;
  config_hash: string;
  events: any[];
}

export interface ReconciliationResult {
  auto_matches: AutoMatch[];
  review_packets: ReviewPacket[];
  traces: DecisionTrace[];
  engine_version: string;
  differential_results: any[];
}
