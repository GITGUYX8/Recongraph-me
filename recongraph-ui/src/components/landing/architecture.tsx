import { Database, GitBranch, Share2 } from "lucide-react";

export function Architecture() {
  return (
    <section className="py-40 bg-[#f7f6f2] relative z-20 overflow-hidden fade-in-section">
      <div className="max-w-7xl mx-auto px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
          <div>
            <h2 className="font-serif text-5xl uppercase tracking-tighter mb-8">
              A spreadsheet sees rows. <br /> <span className="italic text-[#B4B4B4]">ReconGraph sees relationships.</span>
            </h2>
            <p className="font-sans text-lg text-[#1c1c1c]/70 max-w-lg mb-12">
              ReconGraph models financial records as connected evidence, allowing reconciliation to move beyond isolated row-to-row comparison.
            </p>
            <div className="flex gap-8 items-center">
              <div className="flex -space-x-4">
                <div className="w-12 h-12 rounded-full border border-[#e5e4de] bg-white flex items-center justify-center">
                  <Database size={20} className="text-[#1c1c1c]" />
                </div>
                <div className="w-12 h-12 rounded-full border border-[#e5e4de] bg-white flex items-center justify-center">
                  <GitBranch size={20} className="text-[#1c1c1c]" />
                </div>
                <div className="w-12 h-12 rounded-full border border-[#e5e4de] bg-white flex items-center justify-center">
                  <Share2 size={20} className="text-[#1c1c1c]" />
                </div>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#B4B4B4]">Graph architecture</span>
            </div>
          </div>
          <div className="relative">
            <div className="p-8 sm:p-16 border border-[#e5e4de] bg-white aspect-square flex items-center justify-center overflow-hidden">
              {/* Abstract Graph Visual */}
              <div className="relative w-full h-full flex items-center justify-center">
                <div className="absolute w-[80%] h-[80%] border border-dashed border-[#e5e4de] rounded-full"></div>
                <div className="grid grid-cols-2 gap-10 sm:gap-20 relative z-10">
                  <div className="w-16 h-16 border border-[#3d7068] bg-[#f7f6f2] flex items-center justify-center font-mono text-[8px] uppercase text-center p-2">Supplier</div>
                  <div className="w-16 h-16 border border-[#e5e4de] bg-white flex items-center justify-center font-mono text-[8px] uppercase text-center p-2">Invoice</div>
                  <div className="w-16 h-16 border border-[#e5e4de] bg-white flex items-center justify-center font-mono text-[8px] uppercase text-center p-2">Register</div>
                  <div className="w-16 h-16 border border-[#3d7068] bg-[#f7f6f2] flex items-center justify-center font-mono text-[8px] uppercase text-center p-2">GST/Tax</div>
                </div>
                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 400 400">
                  <line x1="150" y1="150" x2="250" y2="150" stroke="#e5e4de" strokeWidth="1" />
                  <line x1="150" y1="150" x2="150" y2="250" stroke="#3d7068" strokeWidth="1" />
                  <line x1="250" y1="150" x2="250" y2="250" stroke="#e5e4de" strokeWidth="1" />
                  <line x1="150" y1="250" x2="250" y2="250" stroke="#3d7068" strokeWidth="1" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
