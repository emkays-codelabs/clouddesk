import Link from "next/link";
import type { Evidence } from "@/lib/types";

/** What a match label means: strong, or related but not conclusive. Scores are shown as they are. */
export function matchLabel(strength: Evidence["strength"]): { text: string; tone: string } {
  if (strength === "strong") return { text: "Strong match", tone: "bg-emerald-100 text-emerald-800" };
  if (strength === "partial") return { text: "Partial match", tone: "bg-amber-100 text-amber-800" };
  return { text: "Match not rated", tone: "bg-slate-100 text-slate-600" };
}

/**
 * The cited knowledge behind a reply: title, a match label, the real score, a short excerpt and the
 * full passage behind an expand control (LLD 12.2). Each card expands on its own.
 */
export function EvidencePanel({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return (
      <p role="status" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
        No sufficiently relevant evidence was found. Do not treat the diagnosis as confirmed.
      </p>
    );
  }
  return (
    <ol aria-label="Evidence" className="space-y-2 text-sm">
      {evidence.map((e, index) => {
        const label = matchLabel(e.strength);
        const full = e.passage && e.passage !== e.snippet.replace(/…$/, "") ? e.passage : null;
        return (
          <li key={e.id} className="rounded-xl border border-sand-200 bg-white p-3">
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold text-brand-900">
                [{index + 1}] {e.title}
              </span>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${label.tone}`}>
                {label.text}
              </span>
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              Knowledge base · {e.source} · score {e.score.toFixed(2)}
            </div>
            <p className="mt-1 text-slate-700">{e.snippet}</p>
            {full ? (
              <details className="mt-1">
                <summary className="cursor-pointer text-xs font-medium text-brand-700">Show full passage</summary>
                <p className="mt-1 whitespace-pre-wrap text-slate-700">{full}</p>
              </details>
            ) : null}
            {e.url ? (
              <Link href={e.url} className="mt-1 inline-block text-xs font-medium text-brand-700 hover:underline">
                View source article →
              </Link>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
