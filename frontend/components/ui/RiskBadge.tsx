const TONES: Record<string, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-red-100 text-red-800",
};

/** The risk level of a plan or an action (docs/04_LLD.md 12.2). */
export function RiskBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${TONES[level] ?? "bg-slate-100 text-slate-700"}`}
    >
      {`risk ${level}`}
    </span>
  );
}
