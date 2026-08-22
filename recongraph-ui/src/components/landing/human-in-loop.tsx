export function HumanInLoop() {
  return (
    <section className="py-32 relative z-20 fade-in-section">
      <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 lg:grid-cols-2 gap-24">
        <div>
          <h2 className="font-serif text-5xl leading-[1.1] uppercase tracking-tighter mb-8">
            AI recommends. <br /> People decide. <br /> <span className="italic text-[#3d7068]">The system learns.</span>
          </h2>
          <p className="font-sans text-lg text-[#1c1c1c]/70">
            ReconGraph closes the gap between automated detection and human expertise, turning every correction into structural organizational intelligence.
          </p>
        </div>
        <div className="flex flex-col justify-between py-8 space-y-12 border-l border-[#e5e4de] pl-12">
          <div className="font-mono text-[12px] opacity-60 uppercase">01 &mdash; AI identifies exception</div>
          <div className="font-mono text-[12px] uppercase">02 &mdash; Human reviews / changes priority</div>
          <div className="font-mono text-[12px] opacity-60 uppercase">03 &mdash; Feedback is recorded</div>
          <div className="font-mono text-[12px] uppercase">04 &mdash; Organization risk profile adapts</div>
          <div className="font-mono text-[12px] opacity-60 uppercase">05 &mdash; Future reconciliation becomes more relevant</div>
        </div>
      </div>
    </section>
  );
}
