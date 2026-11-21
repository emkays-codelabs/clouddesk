const TONES: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  in_progress: "bg-indigo-100 text-indigo-800",
  waiting_on_customer: "bg-amber-100 text-amber-800",
  waiting_on_approval: "bg-amber-100 text-amber-800",
  escalated: "bg-red-100 text-red-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-slate-200 text-slate-700",
};

/** Shows a ticket status with underscores as spaces, e.g. "waiting on approval". */
export function StatusPill({ status }: { status: string }) {
  const tone = TONES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
