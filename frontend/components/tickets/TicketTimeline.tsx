import { humanize } from "@/lib/format";
import type { WorkflowEvent } from "@/lib/types";

/**
 * The AI timeline: each node and tool call with its time, and the tokens a model call used
 * (docs/04_LLD.md 12.2, F13). Prompts and hidden reasoning are never in the events.
 */
export function TicketTimeline({ events }: { events: WorkflowEvent[] }) {
  const shown = events.filter((e) => e.event_type !== "node_started");
  if (shown.length === 0) return <p className="text-sm text-slate-500">No steps recorded yet.</p>;
  return (
    <ol aria-label="Timeline" className="space-y-1 text-xs">
      {shown.map((e) => (
        <li key={e.id} className="flex justify-between gap-2">
          <span>
            <span className="rounded bg-slate-100 px-1.5 py-0.5">{humanize(e.event_type)}</span>{" "}
            {e.tool ?? e.node ?? ""} <span className="text-slate-500">{e.message}</span>
          </span>
          <span className="shrink-0 text-slate-500">{e.duration_ms != null ? `${e.duration_ms} ms` : ""}</span>
        </li>
      ))}
    </ol>
  );
}
