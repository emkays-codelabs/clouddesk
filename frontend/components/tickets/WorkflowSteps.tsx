import type { WorkflowState } from "@/lib/types";

/** The twelve graph steps, in the order the backend declares them (GRAPH_NODES in agents/graph.py). */
export const STEPS: readonly { id: string; label: string }[] = [
  { id: "understand_ticket", label: "Understand ticket" },
  { id: "classify_severity", label: "Classify severity" },
  { id: "customer_context", label: "Customer context" },
  { id: "knowledge_retrieval", label: "Knowledge retrieval" },
  { id: "troubleshooting", label: "Troubleshooting" },
  { id: "resolution_planning", label: "Resolution planning" },
  { id: "risk_check", label: "Risk check" },
  { id: "human_approval", label: "Human approval" },
  { id: "execute_resolution", label: "Execute resolution" },
  { id: "escalation", label: "Escalation" },
  { id: "ticket_summary", label: "Ticket summary" },
  { id: "memory_update", label: "Memory update" },
];

export type StepStatus = "done" | "running" | "waiting" | "pending" | "skipped";
export type Step = { id: string; label: string; status: StepStatus };

const FINISHED = new Set(["completed", "escalated", "failed"]);

/** Turn a workflow state into the status of each of the twelve steps. */
export function deriveSteps(state: WorkflowState | null | undefined): Step[] {
  const done = new Set(state?.completed_nodes ?? []);
  const finished = !!state && FINISHED.has(state.status);
  let runningAssigned = false;
  return STEPS.map(({ id, label }) => {
    if (done.has(id)) return { id, label, status: "done" as const };
    if (state?.status === "waiting_for_approval" && id === "human_approval") {
      return { id, label, status: "waiting" as const };
    }
    if (finished) return { id, label, status: "skipped" as const };
    if (state?.status === "running" && !runningAssigned) {
      runningAssigned = true;
      return { id, label, status: "running" as const };
    }
    return { id, label, status: "pending" as const };
  });
}

const MARK: Record<StepStatus, string> = {
  done: "✓",
  running: "…",
  waiting: "⏸",
  pending: "○",
  skipped: "–",
};

export function WorkflowSteps({ state }: { state: WorkflowState | null | undefined }) {
  return (
    <ol aria-label="Workflow steps" className="space-y-1 text-sm">
      {deriveSteps(state).map((s) => (
        <li
          key={s.id}
          data-status={s.status}
          className={
            s.status === "done"
              ? "text-green-800"
              : s.status === "waiting" || s.status === "running"
                ? "font-medium text-amber-800"
                : "text-slate-400"
          }
        >
          <span aria-hidden className="mr-2 inline-block w-4 text-center">
            {MARK[s.status]}
          </span>
          {s.label}
          <span className="sr-only"> ({s.status})</span>
        </li>
      ))}
    </ol>
  );
}
