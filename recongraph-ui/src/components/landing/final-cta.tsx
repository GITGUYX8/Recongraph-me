import Link from "next/link";

export function FinalCTA() {
  return (
    <section className="py-48 border-t border-[#e5e4de] relative z-10 fade-in-section">
      <div className="max-w-7xl mx-auto px-8 text-center">
        <h2 className="font-serif text-[6vw] uppercase leading-[1] tracking-tighter mb-12">
          Stop chasing mismatches. <br /> <span className="italic">Start understanding them.</span>
        </h2>
        <p className="font-sans text-xl text-[#1c1c1c]/70 mb-16">
          Turn reconciliation into an intelligent investigation workflow.
        </p>
        <Link href="/app" id="final-cta-btn" className="inline-block shadow-drop bg-[#3d7068] text-white px-16 py-8 font-mono text-[12px] uppercase tracking-[0.4em] transition-all hover:translate-y-1 hover:shadow-none">
          Start with ReconGraph &rarr;
        </Link>
      </div>
    </section>
  );
}