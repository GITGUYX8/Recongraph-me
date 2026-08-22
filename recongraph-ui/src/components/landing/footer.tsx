export function Footer() {
  return (
    <footer className="py-12 border-t border-[#e5e4de] bg-[#f7f6f2] relative z-20">
      <div className="max-w-7xl mx-auto px-8 flex flex-col md:flex-row justify-between items-center gap-8">
        <div className="font-mono text-[8px] uppercase tracking-[0.4em] text-[#B4B4B4]">
          &copy; 2024 ReconGraph / Financial Evidence Systems
        </div>
        <div className="flex gap-8">
          <a href="#" id="footer-social-tw" className="font-mono text-[8px] uppercase tracking-[0.4em] hover:text-[#3d7068] transition-colors">Twitter</a>
          <a href="#" id="footer-social-li" className="font-mono text-[8px] uppercase tracking-[0.4em] hover:text-[#3d7068] transition-colors">LinkedIn</a>
        </div>
      </div>
    </footer>
  );
}