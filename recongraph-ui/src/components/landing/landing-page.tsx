"use client";

import { useEffect } from "react";
import { Nav } from "./nav";
import { Hero } from "./hero";
import { WhyRecongraph } from "./why-recongraph";
import { HowItWorks } from "./how-it-works";
import { Investigation } from "./investigation";
import { AdaptiveRisk } from "./adaptive-risk";
import { HumanInLoop } from "./human-in-loop";
import { Features } from "./features";
import { Architecture } from "./architecture";
import { Roadmap } from "./roadmap";
import { FAQ } from "./faq";
import { FinalCTA } from "./final-cta";
import { Footer } from "./footer";

export function LandingPage() {
  useEffect(() => {
    // Simple Fade In Observer
    const observerOptions = {
      threshold: 0.1,
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    }, observerOptions);

    document.querySelectorAll(".fade-in-section").forEach((section) => {
      observer.observe(section);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen relative selection:bg-[#3d7068] selection:text-white bg-[#f7f6f2] text-[#1c1c1c]">
      <div className="fixed inset-0 editorial-grid z-0"></div>
      <div className="structural-line" style={{ left: "25%" }}></div>
      <div className="structural-line" style={{ left: "50%" }}></div>
      <div className="structural-line" style={{ left: "75%" }}></div>

      <Nav />
      <Hero />
      <WhyRecongraph />
      <HowItWorks />
      <Investigation />
      <AdaptiveRisk />
      <HumanInLoop />
      <Features />
      <Architecture />
      <Roadmap />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  );
}