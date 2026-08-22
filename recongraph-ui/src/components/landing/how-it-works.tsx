export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-y border-[#e5e4de] py-32 relative z-10 fade-in-section">
      <div className="max-w-7xl mx-auto px-8">
        <h2 className="font-serif text-5xl uppercase tracking-tighter mb-20 text-center">From Records to Decisions.</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-y-24 gap-x-12">
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">01 — INGEST</div>
            <p className="font-sans text-base leading-relaxed">Purchase Register, GSTR-2B and financial records.</p>
          </div>
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">02 — BUILD THE EVIDENCE GRAPH</div>
            <p className="font-sans text-base leading-relaxed">Connect invoices, GSTINs, vendors, amounts, dates and tax evidence.</p>
          </div>
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">03 — RECONCILE</div>
            <p className="font-sans text-base leading-relaxed">Deterministic rules + graph relationships + calibrated ML identify the strongest matches.</p>
          </div>
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">04 — INVESTIGATE</div>
            <p className="font-sans text-base leading-relaxed">AI analyzes exceptions and explains why records disagree.</p>
          </div>
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">05 — PRIORITIZE</div>
            <p className="font-sans text-base leading-relaxed">Adaptive Risk Engine ranks cases based on financial impact, severity, uncertainty and organization-specific priorities.</p>
          </div>
          <div className="flex flex-col border-l border-[#e5e4de] pl-8">
            <div className="font-mono text-[12px] mb-4 text-[#3d7068]">06 — LEARN</div>
            <p className="font-sans text-base leading-relaxed">Human decisions become feedback that calibrates the organization&rsquo;s future risk profile.</p>
          </div>
        </div>
      </div>
    </section>
  );
}