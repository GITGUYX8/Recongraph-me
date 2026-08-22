import { ArrowRight } from "lucide-react";

export function AdaptiveRisk() {
  return (
    <section className="py-32 border-y border-[#e5e4de] relative z-10 fade-in-section">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex flex-col items-center text-center mb-24">
          <h2 className="font-serif text-5xl leading-[1.1] uppercase tracking-tighter mb-8">
            RECONGRAPH LEARNS WHAT MATTERS TO YOU
          </h2>
          <p className="font-sans text-lg text-[#1c1c1c]/70 max-w-2xl">
            Every organization has different financial priorities. ReconGraph creates an organization-specific risk profile and adapts prioritization based on how that organization reviews exceptions.
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-20">
          <div className="p-12 border border-[#e5e4de] bg-white">
            <div className="font-mono text-[10px] uppercase tracking-[0.4em] mb-8 text-[#B4B4B4]">Company A / Risk Profile</div>
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-[#e5e4de] pb-4">
                <span className="font-serif text-xl">Date Mismatch</span>
                <span className="font-mono text-[10px] text-green-600 px-3 py-1 border border-green-600 uppercase tracking-widest">Low</span>
              </div>
              <div className="flex justify-between items-center border-b border-[#e5e4de] pb-4">
                <span className="font-serif text-xl">GSTIN Mismatch</span>
                <span className="font-mono text-[10px] text-red-600 px-3 py-1 border border-red-600 uppercase tracking-widest">Critical</span>
              </div>
            </div>
          </div>
          <div className="p-12 border border-[#e5e4de] bg-white">
            <div className="font-mono text-[10px] uppercase tracking-[0.4em] mb-8 text-[#B4B4B4]">Company B / Risk Profile</div>
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-[#e5e4de] pb-4">
                <span className="font-serif text-xl">Date Mismatch</span>
                <span className="font-mono text-[10px] text-amber-600 px-3 py-1 border border-amber-600 uppercase tracking-widest">High</span>
              </div>
              <div className="flex justify-between items-center border-b border-[#e5e4de] pb-4">
                <span className="font-serif text-xl">GSTIN Mismatch</span>
                <span className="font-mono text-[10px] text-red-600 px-3 py-1 border border-red-600 uppercase tracking-widest">Critical</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex flex-wrap justify-center items-center gap-6 font-mono text-[10px] uppercase tracking-[0.2em] text-[#B4B4B4]">
          <span>AI Priority</span>
          <ArrowRight size={14} />
          <span className="text-[#1c1c1c]">Human Feedback</span>
          <ArrowRight size={14} />
          <span>Organization Profile</span>
          <ArrowRight size={14} />
          <span className="text-[#1c1c1c]">Future Priorities</span>
        </div>
        <div className="text-center mt-12 font-serif italic text-2xl text-[#1c1c1c]/40">
          &ldquo;One reconciliation engine. Different organizations. Different learned priorities.&rdquo;
        </div>
      </div>
    </section>
  );
}
