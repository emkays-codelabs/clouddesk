import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { StatusPill } from "@/components/ui/StatusPill";

afterEach(cleanup);

describe("StatusPill", () => {
  it("renders the status with underscores as spaces", () => {
    render(<StatusPill status="waiting_on_approval" />);
    expect(screen.getByText("waiting on approval")).toBeTruthy();
  });

  it("uses a distinct tone for escalated tickets", () => {
    render(<StatusPill status="escalated" />);
    expect(screen.getByText("escalated").className).toContain("bg-red-100");
  });

  it("falls back to a neutral tone for an unknown status", () => {
    render(<StatusPill status="mystery" />);
    expect(screen.getByText("mystery").className).toContain("bg-slate-100");
  });
});
