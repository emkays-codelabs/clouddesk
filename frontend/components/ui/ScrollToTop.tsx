"use client";

import { useEffect, useState } from "react";

/** A floating button that appears after scrolling and returns to the top of the page. */
export function ScrollToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 400);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;
  return (
    <button
      type="button"
      aria-label="Scroll to top"
      title="Back to top"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      style={{
        position: "fixed",
        right: 20,
        bottom: 20,
        zIndex: 200,
        width: 44,
        height: 44,
        borderRadius: 14,
        border: "1px solid rgba(255,255,255,.35)",
        background: "linear-gradient(135deg,#059669,#14b8a6)",
        color: "#fff",
        fontSize: 20,
        cursor: "pointer",
        boxShadow: "0 10px 28px rgba(5,150,105,.35)",
      }}
    >
      ↑
    </button>
  );
}
