import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { STEPS, WorkflowSteps, deriveSteps, summarise } from "@/components/tickets/WorkflowSteps";
import type { WorkflowState } from "@/lib/types";

function state(over: Partial<WorkflowState>): WorkflowState {
  return {
    workflow_id: "w",
    ticket_id: "t",
    status: "running",
    current_node: null,
    completed_nodes: [],
    retrieved_docs: [],
    actions: [],
    escalation_required: false,
    approval_status: "not_required",
    errors: [],
    token_usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, estimated_cost_usd: 0 },
    ...over,
  };
}

const statuses = (s: WorkflowState | null) => deriveSteps(s).map((x) => x.status);

describe("deriveSteps", () => {
  it("has the twelve steps the backend graph declares", () => {
    expect(STEPS).toHaveLength(12);
    expect(deriveSteps(null)).toHaveLength(12);
  });

  it("is all pending before any run", () => {
    expect(new Set(statuses(null))).toEqual(new Set(["pending"]));
  });

  it("marks finished steps done and the next one running", () => {
    const s = statuses(state({ completed_nodes: ["understand_ticket", "classify_severity"] }));
    expect(s.slice(0, 3)).toEqual(["done", "done", "running"]);
    expect(s.filter((x) => x === "running")).toHaveLength(1);
  });

  it("shows the approval step as waiting when the run is paused", () => {
    const done = STEPS.slice(0, 7).map((x) => x.id);
    const s = deriveSteps(state({ status: "waiting_for_approval", completed_nodes: done }));
    expect(s.find((x) => x.id === "human_approval")?.status).toBe("waiting");
  });

  it("marks the route not taken as skipped once the run ends", () => {
    const done = [
      "understand_ticket",
      "classify_severity",
      "customer_context",
      "knowledge_retrieval",
      "troubleshooting",
      "resolution_planning",
      "risk_check",
      "escalation",
      "ticket_summary",
      "memory_update",
    ];
    const s = deriveSteps(state({ status: "escalated", completed_nodes: done }));
    expect(s.find((x) => x.id === "human_approval")?.status).toBe("skipped");
    expect(s.find((x) => x.id === "execute_resolution")?.status).toBe("skipped");
    expect(s.find((x) => x.id === "escalation")?.status).toBe("done");
  });

  it("renders every step with its status for assistive technology", () => {
    render(<WorkflowSteps state={state({ completed_nodes: ["understand_ticket"] })} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.getByText("Understand ticket").closest("li")?.getAttribute("data-status")).toBe("done");
  });
});

describe("summarise", () => {
  it("says not run yet at 0 percent with no state", () => {
    expect(summarise(null)).toMatchObject({ label: "Not run yet", percent: 0 });
  });

  it("reports progress while running", () => {
    const s = summarise(state({ completed_nodes: ["understand_ticket", "classify_severity"] }));
    expect(s.label).toBe("Running");
    expect(s.done).toBe(2);
    expect(s.percent).toBeGreaterThan(0);
    expect(s.percent).toBeLessThan(100);
  });

  it("is 100 percent when the run has finished", () => {
    expect(summarise(state({ status: "completed", completed_nodes: ["understand_ticket"] })).percent).toBe(100);
  });

  it("names a run that is waiting for a person", () => {
    expect(summarise(state({ status: "waiting_for_approval" })).label).toBe("Waiting for approval");
  });

  it("renders a progress bar", () => {
    const { container } = render(<WorkflowSteps state={state({ completed_nodes: ["understand_ticket"] })} />);
    expect(container.querySelector('[role="progressbar"]')).not.toBeNull();
  });
});
