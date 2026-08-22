export function Roadmap() {
  return (
    <section className="py-32 border-t border-[#e5e4de] relative z-10 fade-in-section">
      <div className="max-w-7xl mx-auto px-8">
        <h2 className="font-serif text-5xl uppercase tracking-tighter mb-20 text-center">GST is the starting point.</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-12 border border-[#3d7068] bg-[#f7f6f2]">
            <div className="font-mono text-[10px] uppercase mb-8">Today</div>
            <h3 className="font-serif text-2xl mb-6">Purchase Register &harr; GSTR-2B</h3>
            <p className="text-sm text-[#1c1c1c]/70">Seamless reconciliation of primary tax filings with internal records.</p>
          </div>
          <div className="p-12 border border-[#e5e4de]">
            <div className="font-mono text-[10px] uppercase mb-8 opacity-40">Next</div>
            <h3 className="font-serif text-2xl mb-6">Invoices &harr; Vendors &harr; Ledgers</h3>
            <p className="text-sm text-[#1c1c1c]/70">Expanding to holistic enterprise data integrity across all internal systems.</p>
          </div>
          <div className="p-12 border border-[#e5e4de]">
            <div className="font-mono text-[10px] uppercase mb-8 opacity-40">Vision</div>
            <h3 className="font-serif text-2xl mb-6">Ledger &harr; Payments &harr; Banking</h3>
            <p className="text-sm text-[#1c1c1c]/70">Real-time automated evidence verification for global treasury operations.</p>
          </div>
        </div>
        <p className="mt-16 text-center font-sans text-[#B4B4B4]">
          ReconGraph is designed as a financial evidence intelligence layer, with GST reconciliation as the first use case.
        </p>
      </div>
    </section>
  );
}
