from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from recongraph.domain.records import PurchaseRecord, GSTRecord
from recongraph.graph.decision import DecisionAction, ReconciliationDecision
from recongraph.graph.fusion_explainability import ExplanationArtifact
from recongraph.graph.hypotheses import EvaluatedHypothesis
from recongraph.graph.risk import RiskProfile, RiskEngine

if TYPE_CHECKING:
    from recongraph.domain.document.layout import BoundingBox
    from recongraph.graph.candidate import CandidateGraph


@dataclass(frozen=True)
class ReviewOutcome:
    """The mutable workflow state owned by the human/AI reviewer."""
    reviewer_id: str
    final_action: str
    comments: str


@dataclass(frozen=True)
class ReviewPacket:
    """
    An immutable, curated workspace required for a human/AI to resolve a complex decision.

    Stage 8G additions:
      - highlight_regions: Bounding boxes of low-confidence OCR zones to surface in the UI.
      - ocr_warnings: Human-readable warnings derived from OCR provenance analysis.

    headline: One-line human-readable summary of the decision — feeds the review queue UI.
    """
    packet_id: str
    action: DecisionAction
    purchases: tuple[PurchaseRecord, ...]
    gsts: tuple[GSTRecord, ...]
    explanation: ExplanationArtifact | None
    competitors: tuple[EvaluatedHypothesis, ...]
    checklist: tuple[str, ...]
    headline: str = ""
    highlight_regions: "tuple[BoundingBox, ...]" = ()
    ocr_warnings: tuple[str, ...] = ()
    ml_confidence: float | None = None
    llm_explanation: str | None = None
    llm_citation: str | None = None
    ai_provenance: dict | None = None
    risk_profile: RiskProfile | None = None


from recongraph.domain.reliability.dimensions import ExtractionQuality
from recongraph.domain.reliability import convert_ocr_report_to_envelope

def _collect_ocr_data_from_records(
    purchases: list[PurchaseRecord],
    gsts: list[GSTRecord]
) -> tuple["tuple[BoundingBox, ...]", "tuple[str, ...]"]:
    """
    Collect OCR highlight boxes and warnings directly from the ReliabilityEnvelope
    attached to the underlying records.
    """
    all_boxes: list[Any] = []
    all_warnings: set[str] = set()

    for record in purchases + gsts:
        env = getattr(record, "reliability_envelope", None)
        if not env:
            if report := getattr(record, "ocr_confidence_report", None):
                env = convert_ocr_report_to_envelope(report)
            
        if not env:
            continue
            
        for field in env.profiles:
            q = field.profile.extraction_quality
            # Degraded, Low, Failed are mapped to warnings
            if q in (ExtractionQuality.DEGRADED, ExtractionQuality.LOW, ExtractionQuality.FAILED):
                if "box" in field.profile.audit_metadata:
                    all_boxes.append(field.profile.audit_metadata["box"])
                all_warnings.add(f"OCR_{field.field_name.upper()}_WARNING")

    return tuple(all_boxes), tuple(all_warnings)


class ReviewPacketBuilder:
    """Constructs ReviewPackets exclusively for non-automated decisions."""

    def __init__(self) -> None:
        self._counter = 0

    def _generate_headline(self, action: DecisionAction, purchases: list[PurchaseRecord],
                           gsts: list[GSTRecord], competitors: tuple) -> str:
        """Produce a one-line human-readable summary for the review queue UI."""
        p_refs = ", ".join(p.reference or p.record_id for p in purchases[:2])
        g_refs = ", ".join(g.reference or g.record_id for g in gsts[:2])
        top_score = competitors[0].score if competitors else None
        score_str = f"{top_score:.2f}" if top_score is not None else "?"

        if action == DecisionAction.REVIEW_AMBIGUOUS:
            return f"Ambiguous: {p_refs} ↔ {g_refs} — competing hypotheses within margin"
        elif action == DecisionAction.REVIEW_WEAK:
            violations = competitors[0].violations if competitors else frozenset()
            if "tax_identity_conflict" in violations:
                return f"Tax conflict: {p_refs} ↔ {g_refs} — GSTIN identity mismatch (score {score_str})"
            elif "severe_amount_conflict" in violations:
                return f"Amount mismatch: {p_refs} ↔ {g_refs} — significant amount discrepancy (score {score_str})"
            else:
                return f"Weak evidence: {p_refs} ↔ {g_refs} — score {score_str} below threshold"
        elif action == DecisionAction.NO_MATCH:
            if purchases:
                return f"No match: purchase {p_refs} — no candidate GST record found"
            else:
                return f"No match: GST {g_refs} — no candidate purchase record found"
        else:
            return f"Review required: {p_refs} ↔ {g_refs}"

    def _generate_checklist(self, explanation: ExplanationArtifact | None, ocr_warnings: tuple[str, ...] = ()) -> tuple[str, ...]:
        checklist = []
        if explanation is None and not ocr_warnings:
            return ("General manual review",)

        if explanation is not None:
            # Use Layer 3 missingness and contradictions
            contradicted = explanation.technical_details.get("contradicted", [])
            if "TAX_NODE" in contradicted:
                checklist.append("Verify GST tax filing manually")
            if "FINANCIAL_NODE" in contradicted:
                checklist.append("Verify exact invoice amounts and potential split payments")
            if "TEMPORAL_NODE" in contradicted:
                checklist.append("Verify transaction date against posting date")

            action_str = explanation.executive_summary.get("decision")
            if action_str == DecisionAction.REVIEW_AMBIGUOUS.value:
                checklist.append("Disambiguate competing hypotheses manually")

        # Inject OCR warnings as checklist items
        for warning in ocr_warnings:
            checklist.append(warning)

        if not checklist:
            checklist.append("General manual review")

        return tuple(checklist)

    def build(
        self,
        decision: ReconciliationDecision,
        explanation: ExplanationArtifact | None,
        graph: "CandidateGraph",
        ml_confidence: float | None = None,
        llm_explanation: str | None = None,
        llm_citation: str | None = None,
        ai_provenance: dict | None = None
    ) -> ReviewPacket | None:

        if decision.action == DecisionAction.AUTO_MATCH:
            return None

        self._counter += 1
        packet_id = f"RP-{self._counter:05d}"

        purchases = []
        gsts = []

        target_hypothesis = decision.selected_hypothesis
        if not target_hypothesis and decision.competitors:
            target_hypothesis = decision.competitors[0]

        highlight_regions: tuple['BoundingBox', ...] = ()
        ocr_warnings: tuple[str, ...] = ()

        if target_hypothesis:
            for urn in target_hypothesis.hypothesis.matched_nodes:
                if urn.startswith("urn:recongraph:purchase:"):
                    purchases.append(graph.nodes[urn])
                elif urn.startswith("urn:recongraph:gst:"):
                    gsts.append(graph.nodes[urn])
            # Collect OCR data from the underlying records directly
            highlight_regions, ocr_warnings = _collect_ocr_data_from_records(purchases, gsts)

        checklist = self._generate_checklist(explanation, ocr_warnings)
        curated_competitors = decision.competitors[:3]
        headline = self._generate_headline(decision.action, purchases, gsts, curated_competitors)

        risk_profile = RiskEngine.assess(
            purchases=tuple(purchases),
            gsts=tuple(gsts),
            competitors=curated_competitors,
            ml_confidence=ml_confidence
        )

        return ReviewPacket(
            packet_id=packet_id,
            action=decision.action,
            purchases=tuple(purchases),
            gsts=tuple(gsts),
            explanation=explanation,
            competitors=curated_competitors,
            checklist=checklist,
            headline=headline,
            highlight_regions=highlight_regions,
            ocr_warnings=tuple(sorted(ocr_warnings)),
            ml_confidence=ml_confidence,
            llm_explanation=llm_explanation,
            llm_citation=llm_citation,
            ai_provenance=ai_provenance,
            risk_profile=risk_profile
        )

    def build_single_leftover(self, urn: str, graph: "CandidateGraph") -> ReviewPacket | None:
        self._counter += 1
        packet_id = f"RP-{self._counter:05d}"

        purchases = []
        gsts = []

        if urn.startswith("urn:recongraph:purchase:"):
            purchases.append(graph.nodes[urn])
        elif urn.startswith("urn:recongraph:gst:"):
            gsts.append(graph.nodes[urn])

        if not purchases and not gsts:
            return None

        headline = self._generate_headline(DecisionAction.NO_MATCH, purchases, gsts, ())
        risk_profile = RiskEngine.assess(
            purchases=tuple(purchases),
            gsts=tuple(gsts),
            competitors=(),
            ml_confidence=None
        )

        return ReviewPacket(
            packet_id=packet_id,
            action=DecisionAction.NO_MATCH,
            purchases=tuple(purchases),
            gsts=tuple(gsts),
            explanation=None,
            competitors=(),
            checklist=("Review unmatched record",),
            headline=headline,
            highlight_regions=(),
            ocr_warnings=(),
            ml_confidence=None,
            llm_explanation=None,
            risk_profile=risk_profile
        )
