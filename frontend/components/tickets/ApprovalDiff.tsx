import type { PlannedAction } from "@/lib/types";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { formatMoney } from "@/lib/format";

function show(value: unknown): string {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (value === null || value === undefined) return "-";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

/**
 * What the approver is about to allow: the tool, every argument and why it needs a person
 * (docs/04_LLD.md 12.2). v1 approves or rejects as proposed; editing arguments is not built.
 */
export function ApprovalDiff({
  action,
  riskLevel,
  reason,
}: {
  action: PlannedAction;
  riskLevel: string;
  reason?: string;
}) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium">{action.tool}</span>
        <RiskBadge level={riskLevel} />
      </div>
      {action.description ? <p>{action.description}</p> : null}
      <table className="w-full text-left">
        <thead className="text-xs text-slate-500">
          <tr>
            <th className="py-1">Argument</th>
            <th>Proposed value</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {Object.entries(action.arguments).map(([name, value]) => (
            <tr key={name}>
              <td className="py-1 font-mono text-xs">{name}</td>
              <td className="font-mono text-xs">
                {name === "amount" && typeof value === "number" ? formatMoney(value) : show(value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {reason ? <p className="text-xs text-slate-600">Why a person must decide: {reason}</p> : null}
    </div>
  );
}
