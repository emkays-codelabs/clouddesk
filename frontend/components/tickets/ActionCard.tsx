import type { PlannedAction, ResolutionAction } from "@/lib/types";

const TONES: Record<string, string> = {
  planned: "bg-slate-100 text-slate-700",
  pending_approval: "bg-amber-100 text-amber-800",
  approved: "bg-blue-100 text-blue-800",
  executed: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  failed: "bg-red-100 text-red-800",
};

type Props = {
  action: Pick<PlannedAction, "tool" | "requires_approval"> & { description?: string };
  /** proposed, approved, executed, ... (docs/04_LLD.md 12.2) */
  status: ResolutionAction["status"];
};

/** One action the AI proposed or took, with where it stands. */
export function ActionCard({ action, status }: Props) {
  return (
    <div className="flex items-start justify-between gap-2 rounded border border-slate-200 p-2 text-sm">
      <div>
        <div className="font-medium">{action.tool}</div>
        {action.description ? <div className="text-slate-600">{action.description}</div> : null}
        {action.requires_approval ? <div className="text-xs text-amber-800">needs a person&apos;s approval</div> : null}
      </div>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${TONES[status] ?? TONES.planned}`}>
        {status.replaceAll("_", " ")}
      </span>
    </div>
  );
}
