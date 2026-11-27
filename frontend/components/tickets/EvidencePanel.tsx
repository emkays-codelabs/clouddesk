import type { Evidence } from "@/lib/types";

/** The cited knowledge behind a reply: each source with its score and the passage used (LLD 12.2). */
export function EvidencePanel({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return <p className="text-sm text-slate-500">No evidence was retrieved.</p>;
  }
  return (
    <ol aria-label="Evidence" className="space-y-2 text-sm">
      {evidence.map((e, index) => (
        <li key={e.id} className="rounded border border-slate-200 p-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-medium">
              [{index + 1}] {e.title}
            </span>
            <span className="text-xs text-slate-500">score {e.score.toFixed(2)}</span>
          </div>
          <div className="text-xs text-slate-500">{e.source}</div>
          <p className="mt-1 text-slate-700">{e.snippet}</p>
        </li>
      ))}
    </ol>
  );
}
