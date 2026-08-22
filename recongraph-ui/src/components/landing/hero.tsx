import { FileText, Landmark } from "lucide-react";
import Link from "next/link";

export function Hero() {
  return (
    <section className="relative pt-48 pb-40 z-10 fade-in-section">
      <div className="max-w-7xl mx-auto px-8 flex flex-col items-center text-center">
        <h1 className="font-serif text-[8vw] leading-[0.9] uppercase font-light tracking-tighter mb-12">
          Reconciliation, <br />
          <span className="italic text-[#B4B4B4]">Beyond</span> <br />
          Matching.
        </h1>
        <p className="max-w-2xl font-sans text-xl text-[#1c1c1c]/70 mb-12">
          ReconGraph doesn&apos;t just find mismatches. It investigates them &mdash; connecting financial evidence, explaining discrepancies, prioritizing risk, and helping teams decide what needs attention.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link href="/app" id="cta-hero-start" className="cta-button-hover group relative overflow-hidden bg-[#3d7068] text-white px-10 py-5 font-mono text-[10px] uppercase tracking-[0.25em] transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] rounded-[2px] w-full sm:w-auto text-center inline-block">
            <span className="relative z-10 tracking-slide transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]">
              Start a Reconciliation
            </span>
            <div className="bg-overlay absolute inset-0 bg-white/20 translate-y-full transition-transform duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] z-0"></div>
          </Link>
          <Link href="#how-it-works" id="cta-hero-how" className="px-10 py-5 border border-[#e5e4de] font-mono text-[10px] uppercase tracking-[0.25em] hover:bg-white transition-colors duration-500 rounded-[2px] w-full sm:w-auto text-center inline-block">
            See How It Works
          </Link>
        </div>

        {/* Subtle Hero Visual */}
        <div className="mt-24 w-full max-w-4xl flex items-center justify-between border-y border-[#e5e4de] py-12 px-2 sm:px-8 overflow-hidden">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border border-[#e5e4de] flex items-center justify-center bg-white">
              <FileText className="text-xl text-[#1c1c1c]" size={20} />
            </div>
            <span className="font-mono text-[8px] uppercase tracking-[0.3em] hidden sm:block">Purchase Register</span>
          </div>
          <div className="h-[1px] flex-1 bg-[#e5e4de] mx-4 sm:mx-8 relative overflow-hidden hidden sm:block">
            <div className="absolute top-0 left-0 h-full w-20 bg-[#3d7068] scan-line"></div>
          </div>
          <div className="px-4 sm:px-6 py-4 border border-[#3d7068] bg-[#f7f6f2] z-10">
            <span className="font-serif text-lg tracking-tight uppercase">ReconGraph</span>
          </div>
          <div className="h-[1px] flex-1 bg-[#e5e4de] mx-4 sm:mx-8 relative overflow-hidden hidden sm:block">
            <div className="absolute top-0 left-0 h-full w-20 bg-[#3d7068] scan-line" style={{ animationDelay: "1s" }}></div>
          </div>
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border border-[#e5e4de] flex items-center justify-center bg-white">
              <Landmark className="text-xl text-[#1c1c1c]" size={20} />
            </div>
            <span className="font-mono text-[8px] uppercase tracking-[0.3em] hidden sm:block">GSTR-2B</span>
          </div>
        </div>
      </div>
    </section>
  );
}