"""Core reconciliation execution, shared by the API and the worker.

Kept separate from the FastAPI app so the worker can run the engine without
importing request-handling code.
"""

from recongraph.config import ReconGraphConfig
from recongraph.engine import ReconGraphEngine
from recongraph.plugins.core_providers import (
    FinancialEvidenceProvider,
    ReferenceEvidenceProvider,
    TaxEvidenceProvider,
    TemporalEvidenceProvider,
    VendorEvidenceProvider,
)
from recongraph.domain.vendor.context import VendorIdentityContext
from recongraph.matching.reference_evidence import (
    ReferenceEvidenceContext,
    ReferenceEvidencePolicy,
    build_reference_corpus_profile,
)


def _build_providers(purchases, gsts):
    corpus = build_reference_corpus_profile([r.reference for r in purchases + gsts])
    ref_ctx = ReferenceEvidenceContext(corpus, ReferenceEvidencePolicy())
    vendor_ctx = VendorIdentityContext(corpus_profile=None)
    return [
        FinancialEvidenceProvider(),
        TemporalEvidenceProvider(),
        TaxEvidenceProvider(),
        VendorEvidenceProvider(vendor_ctx),
        ReferenceEvidenceProvider(ref_ctx),
    ]


def run_engine(purchases, gsts):
    providers = _build_providers(purchases, gsts)
    engine = ReconGraphEngine(config=ReconGraphConfig(), providers=providers)
    return engine.reconcile(purchases, gsts)