import { describe, expect, it } from "vitest";
import { NAV_ITEMS } from "@/components/layout/nav";

describe("nav", () => {
  it("lists every console page exactly once", () => {
    const hrefs = NAV_ITEMS.map((i) => i.href);
    expect(hrefs).toEqual([
      "/dashboard",
      "/tickets",
      "/customers",
      "/knowledge",
      "/escalations",
      "/agents",
      "/audit",
      "/settings",
    ]);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("gives every item a label", () => {
    expect(NAV_ITEMS.every((i) => i.label.length > 0)).toBe(true);
  });
});
