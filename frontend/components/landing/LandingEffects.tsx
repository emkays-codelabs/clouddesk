"use client";

import { useEffect, useState } from "react";

/** Reveal-on-scroll for the landing page. Without this script every section is simply visible. */
export function LandingEffects() {
  useEffect(() => {
    const root = document.querySelector(".landing");
    if (!root || typeof IntersectionObserver === "undefined") return;
    root.classList.add("reveal-ready");
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        }),
      { threshold: 0.12 },
    );
    root.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => {
      observer.disconnect();
      root.classList.remove("reveal-ready");
    };
  }, []);
  return null;
}

/** The small-screen menu button: toggles the links and tells assistive technology its state. */
export function MobileMenuButton() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const links = document.getElementById("landing-links");
    links?.classList.toggle("open", open);
  }, [open]);
  return (
    <button
      type="button"
      className="mobile"
      aria-label="Menu"
      aria-expanded={open}
      aria-controls="landing-links"
      onClick={() => setOpen((v) => !v)}
    >
      ☰
    </button>
  );
}
