import { viewDiagnosis } from "@/lib/diagnosis";

type Diagnosis = {
  problem?: string;
  probable_causes?: string[];
  troubleshooting_steps?: string[];
};

/**
 * The diagnosis in three parts: what is probably wrong, what to do (numbered, no repeats), and what
 * must not be done (warning style, only for genuine restrictions).
 */
export function DiagnosisPanel({ diagnosis }: { diagnosis: Diagnosis }) {
  const view = viewDiagnosis(diagnosis);
  return (
    <div className="space-y-3 text-sm">
      <section aria-label="Diagnosis">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Diagnosis</h4>
        <p className="mt-1">{view.problem}</p>
        {view.causes.length ? (
          <ul className="mt-1 list-disc pl-5 text-slate-700">
            {view.causes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        ) : null}
      </section>
      {view.actions.length ? (
        <section aria-label="Recommended actions">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Recommended actions</h4>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5">
            {view.actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ol>
        </section>
      ) : null}
      {view.restrictions.length ? (
        <section aria-label="Safety restrictions" className="rounded-xl border border-amber-300 bg-amber-50 p-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800">Safety restrictions</h4>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-amber-900">
            {view.restrictions.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
