const TONES: Record<string, string> = {
  new: "bg-sky-100 text-sky-800",
  in_progress: "bg-teal-100 text-teal-800",
  waiting_on_customer: "bg-amber-100 text-amber-800",
  waiting_on_approval: "bg-amber-100 text-amber-800",
  escalated: "bg-rose-100 text-rose-800",
  resolved: "bg-emerald-100 text-emerald-800",
  closed: "bg-slate-200 text-slate-700",
};

/** Shows a ticket status with underscores as spaces, e.g. "waiting on approval". */
export function StatusPill({ status }: { status: string }) {
  const tone = TONES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${tone}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
