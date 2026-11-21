import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { EmptyState } from "@/components/ui/EmptyState";

afterEach(cleanup);

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(<EmptyState title="No tickets" description="Nothing to show" />);
    expect(screen.getByText("No tickets")).toBeTruthy();
    expect(screen.getByText("Nothing to show")).toBeTruthy();
  });

  it("renders an action only when one is given", () => {
    const { rerender } = render(<EmptyState title="No tickets" />);
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<EmptyState title="No tickets" action={<button>Create</button>} />);
    expect(screen.getByRole("button", { name: "Create" })).toBeTruthy();
  });
});
