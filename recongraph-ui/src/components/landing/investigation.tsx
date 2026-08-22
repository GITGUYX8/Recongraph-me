import { CheckCircle, AlertTriangle, AlertCircle } from "lucide-react";
import Link from "next/link";

export function Investigation() {
  return (
    <section className="py-32 bg-[#f7f6f2] relative z-20 fade-in-section">
      <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
        <div>
          <h2 className="font-serif text-5xl leading-[1.1] uppercase tracking-tighter mb-8">
            Matching finds the exception. <br /> <span className="italic text-[#3d7068]">AI investigates it.</span>
          </h2>
          <p className="font-sans text-lg text-[#1c1c1c]/70 mb-10 max-w-lg">
            ReconGraph creates deep contextual analysis for every discrepancy, allowing your team to move past row-matching into actual financial investigation.
          </p>
          <Link href="/app" id="cta-investigate" className="inline-block font-mono text-[10px] uppercase tracking-[0.2em] border border-[#e5e4de] px-8 py-4 hover:bg-[#1c1c1c] hover:text-[#f7f6f2] transition-all">
            Explore Case Analysis
          </Link>
        </div>
        
        <div className="bg-white border border-[#e5e4de] p-8 rounded-[2px] shadow-sm">
          <div className="flex justify-between items-start mb-8">
            <div>
              <div className="font-mono text-[10px] text-[#B4B4B4] uppercase tracking-widest mb-1">Case ID</div>
              <div className="font-serif text-xl">Invoice #INV-8291</div>
            </div>
            <div className="text-right">
              <div className="font-mono text-[10px] text-[#3d7068] uppercase tracking-widest mb-1">Likely Match</div>
              <div className="font-serif text-xl text-[#3d7068]">87.2% Confidence</div>
            </div>
          </div>
          
          <div className="space-y-4 mb-8">
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider">
              <CheckCircle size={16} className="text-[#3d7068]" />
              <span>GSTIN matches</span>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider">
              <CheckCircle size={16} className="text-[#3d7068]" />
              <span>Supplier matches</span>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider">
              <CheckCircle size={16} className="text-[#3d7068]" />
              <span>Taxable amount matches</span>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-amber-600">
              <AlertTriangle size={16} />
              <span>Invoice date differs</span>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-red-600">
              <AlertCircle size={16} />
              <span>₹50 amount difference</span>
            </div>
          </div>
          
          <div className="p-6 bg-[#f7f6f2] border-l-2 border-[#3d7068] mb-8">
            <div className="font-mono text-[8px] uppercase tracking-[0.3em] mb-3 text-[#3d7068]">AI Assessment</div>
            <p className="font-serif text-lg italic leading-relaxed">
              &ldquo;These records are likely associated with the same transaction. The discrepancy appears minor, but the filing period should be verified.&rdquo;
            </p>
          </div>
          
          <Link href="/app" id="card-review-btn" className="block text-center w-full bg-[#3d7068] text-white py-4 font-mono text-[10px] uppercase tracking-[0.3em] hover:bg-[#2c524c] transition-colors">
            Review Case
          </Link>
        </div>
      </div>
    </section>
  );
}
