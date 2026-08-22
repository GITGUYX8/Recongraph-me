export function FAQ() {
  return (
    <section id="faq" className="py-32 border-t border-[#e5e4de] relative z-20 fade-in-section">
      <div className="max-w-3xl mx-auto px-8">
        <h2 className="font-serif text-5xl uppercase tracking-tighter mb-20 text-center">Frequently Asked Questions</h2>
        <div className="space-y-12">
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: What is ReconGraph?</div>
            <div className="font-sans text-xl">A: AI-assisted financial reconciliation and investigation platform.</div>
          </div>
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: Is ReconGraph just an invoice matching tool?</div>
            <div className="font-sans text-xl">A: No. Matching is only the first step; ReconGraph investigates, explains and prioritizes exceptions.</div>
          </div>
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: How does AI help?</div>
            <div className="font-sans text-xl">A: AI investigates discrepancies, explains evidence and assists prioritization through contextual reasoning.</div>
          </div>
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: Can different companies have different priorities?</div>
            <div className="font-sans text-xl">A: Yes. Each organization can have its own adaptive risk profile calibrated by human feedback.</div>
          </div>
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: Does ReconGraph learn from human feedback?</div>
            <div className="font-sans text-xl">A: Yes. Human decisions become organization-specific feedback that improves the relevance of future investigations.</div>
          </div>
          <div className="group">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#3d7068] mb-4">Q: Is GST the only use case?</div>
            <div className="font-sans text-xl">A: GST is the initial case; the architecture is designed for financial evidence across invoices, ledgers, payments and banking.</div>
          </div>
        </div>
      </div>
    </section>
  );
}