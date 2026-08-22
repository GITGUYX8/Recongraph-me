from dataclasses import dataclass, field
from typing import List, Tuple
from recongraph.domain.records import PurchaseRecord, GSTRecord
from recongraph.graph.hypotheses import EvaluatedHypothesis

@dataclass
class RiskProfile:
    priority: str
    score: int
    reasons: List[str]
    financial_impact: float

class RiskEngine:
    @staticmethod
    def assess(
        purchases: Tuple[PurchaseRecord, ...],
        gsts: Tuple[GSTRecord, ...],
        competitors: Tuple[EvaluatedHypothesis, ...],
        ml_confidence: float | None = None
    ) -> RiskProfile:
        score = 0
        reasons = []
        financial_impact = 0.0

        hyp = competitors[0] if competitors else None
        
        # Determine absolute difference and financial impact
        if hyp and getattr(hyp, "supporting_evidence", None):
            # Try to get financial impact from semantic evaluation if available
            amt_contrib = getattr(hyp.supporting_evidence, "contributions", {}).get("amount")
            if amt_contrib and getattr(amt_contrib, "metadata", {}).get("interpretation"):
                diff = amt_contrib.metadata["interpretation"].get("absolute_difference")
                if diff:
                    try:
                        financial_impact = float(diff)
                    except ValueError:
                        pass

        # If we couldn't extract it semantically, compute it deterministically
        if financial_impact == 0.0 and purchases and gsts:
            try:
                p_amt = float(purchases[0].amount) if purchases[0].amount else 0.0
                g_amt = float(gsts[0].amount) if gsts[0].amount else 0.0
                financial_impact = abs(g_amt - p_amt)
            except ValueError:
                pass

        # Score based on financial impact
        if financial_impact > 0:
            if financial_impact < 100:
                reasons.append(f"Minor amount difference (₹{financial_impact:,.2f})")
            elif financial_impact <= 5000:
                score += 20
                reasons.append(f"Moderate amount difference (₹{financial_impact:,.2f})")
            elif financial_impact <= 50000:
                score += 40
                reasons.append(f"Significant amount difference (₹{financial_impact:,.2f})")
            else:
                score += 60
                reasons.append(f"Severe amount difference (₹{financial_impact:,.2f})")

        # Score based on ML Confidence
        if ml_confidence is not None:
            if ml_confidence < 0.5:
                score += 30
                reasons.append("Low engine match confidence")
            elif ml_confidence < 0.8:
                score += 15
                reasons.append("Moderate engine match confidence")
            else:
                reasons.append("High engine match confidence")
        else:
            score += 20
            reasons.append("Uncertain match confidence")

        # Assess Violations
        violations = hyp.violations if hyp else frozenset()
        
        if "SEVERE_AMOUNT_CONFLICT" in violations or "severe_amount_conflict" in violations:
            score += 40
            if "Severe amount conflict" not in reasons:
                reasons.append("Severe amount conflict")

        if "AMOUNT_MULTIPLE" in violations or "amount_multiple" in violations:
            score += 30
            reasons.append("Possible duplicate or consolidated invoice (Multiple of amount)")
            
        if any(v in violations for v in ["INVOICE_DATE_MISMATCH", "invoice_date_mismatch", "TEMPORAL_CONFLICT", "temporal_conflict"]):
            score += 15
            reasons.append("Date or filing period mismatch")

        # Check GSTIN Mismatch
        p_gstin = purchases[0].tax_identity if purchases else None
        g_gstin = gsts[0].tax_identity if gsts else None
        if p_gstin and g_gstin and p_gstin != g_gstin:
            score += 30
            reasons.append(f"GSTIN mismatch ({p_gstin} vs {g_gstin})")

        # Cap score at 100
        score = min(score, 100)

        # Determine Priority Level
        priority = "LOW"
        if score >= 70:
            priority = "HIGH"
        elif score >= 40:
            priority = "MEDIUM"

        return RiskProfile(
            priority=priority,
            score=score,
            reasons=reasons,
            financial_impact=financial_impact
        )
