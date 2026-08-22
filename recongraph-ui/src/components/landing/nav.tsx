"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };
    window.addEventListener("scroll", handleScroll);
    handleScroll(); // Check initial state
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      id="main-nav"
      className={`fixed top-0 left-0 w-full z-50 nav-transition ${
        scrolled
          ? "bg-white/90 backdrop-blur-md border-b border-[#e5e4de] pt-4 pb-4"
          : "pt-8 pb-4"
      }`}
    >
      <div className="max-w-7xl mx-auto px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-[1px] bg-[#1c1c1c] w-6"></div>
          <Link
            href="/"
            id="nav-brand-logo"
            className="font-serif text-[20px] uppercase tracking-tighter"
          >
            ReconGraph
          </Link>
          <div className="h-[1px] bg-[#1c1c1c] w-8"></div>
        </div>
        <div className="hidden md:flex items-center gap-12">
          <Link
            href="#why-recong"
            id="nav-link-why"
            className="font-mono text-[10px] uppercase tracking-[0.3em] hover:opacity-60 transition-opacity"
          >
            Why ReconGraph
          </Link>
          <Link
            href="#how-it-works"
            id="nav-link-how"
            className="font-mono text-[10px] uppercase tracking-[0.3em] hover:opacity-60 transition-opacity"
          >
            How It Works
          </Link>
          <Link
            href="#features"
            id="nav-link-features"
            className="font-mono text-[10px] uppercase tracking-[0.3em] hover:opacity-60 transition-opacity"
          >
            Features
          </Link>
          <Link
            href="#faq"
            id="nav-link-faq"
            className="font-mono text-[10px] uppercase tracking-[0.3em] hover:opacity-60 transition-opacity"
          >
            FAQ
          </Link>
          <Link
            href="/app"
            id="nav-cta-demo"
            className="font-mono text-[10px] uppercase tracking-[0.3em] border border-[#e5e4de] px-4 py-2 hover:bg-[#1c1c1c] hover:text-[#f7f6f2] transition-all"
          >
            Try Demo &rarr;
          </Link>
        </div>
      </div>
    </nav>
  );
}