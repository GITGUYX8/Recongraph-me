import { ArrowRight } from "lucide-react";

export function WhyRecongraph() {
  return (
    <section id="why-recong" className="border-t border-[#e5e4de] bg-[#f7f6f2] relative z-20 overflow-hidden fade-in-section">
      <div className="max-w-7xl mx-auto py-32 px-8 grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
        <div>
          <h2 className="font-serif text-6xl leading-[1.1] uppercase tracking-tighter mb-8">
            The problem isn&rsquo;t matching. <br /> <span className="italic text-[#B4B4B4]">It&rsquo;s understanding.</span>
          </h2>
          <p className="font-sans text-lg text-[#1c1c1c]/70 mb-12 max-w-lg">
            Financial reconciliation is not simply about finding two records that don&rsquo;t match. A discrepancy can be a timing difference, missing evidence, duplicate, data-entry issue, or genuine contradiction.
          </p>
        </div>
        
        <div className="grid grid-cols-1 gap-8">
          <div className="p-8 border border-[#e5e4de] bg-white">
            <span className="font-mono text-[10px] text-[#B4B4B4] uppercase block mb-6 tracking-widest">Traditional systems stop at:</span>
            <div className="flex items-center gap-8">
              <span className="font-serif text-3xl opacity-30">MATCH</span>
              <div className="h-[1px] w-12 bg-[#e5e4de]"></div>
              <span className="font-serif text-3xl uppercase tracking-tighter text-[#1c1c1c]">Mismatch</span>
            </div>
          </div>
          
          <div className="p-8 border border-[#3d7068] bg-[#f7f6f2] relative">
            <span className="font-mono text-[10px] text-[#3d7068] uppercase block mb-6 tracking-widest">ReconGraph goes further:</span>
            <div className="flex flex-wrap items-center gap-4 font-serif text-2xl uppercase tracking-tighter">
              <span>Detect</span>
              <ArrowRight className="text-[#3d7068]" size={16} />
              <span>Understand</span>
              <ArrowRight className="text-[#3d7068]" size={16} />
              <span>Prioritize</span>
              <ArrowRight className="text-[#3d7068]" size={16} />
              <span>Act</span>
              <ArrowRight className="text-[#3d7068]" size={16} />
              <span>Learn</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
