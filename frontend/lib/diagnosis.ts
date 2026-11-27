/**
 * Presentation helpers for a diagnosis: remove repeated steps and keep restrictions apart from actions.
 * Display only. Nothing here changes what the backend decided, and no step is invented: a step is
 * dropped only when another step already says the same thing.
 */

const FILLER = new Set(
  "a an the and or of to for with in on at by is are be any all it its this that your their".split(" "),
);

const NUMBERING = /^\s*(\d+[.)]|[-*•])\s*/;

/** A step as plain text: no leading number or bullet. */
export function stripNumbering(step: string): string {
  return step.replace(NUMBERING, "").trim();
}

function contentWords(step: string): string[] {
  const words = stripNumbering(step).toLowerCase().match(/[a-z0-9]+/g) ?? [];
  return words
    .filter((w) => !FILLER.has(w))
    .map((w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w));
}

/** Two steps say the same thing: identical, or one restates the other with extra words (mirrors the backend). */
export function isDuplicateStep(a: string, b: string): boolean {
  const wa = contentWords(a);
  const wb = contentWords(b);
  if (wa.join(" ") === wb.join(" ")) return true;
  const [shorter, longer] = [new Set(wa), new Set(wb)].sort((x, y) => x.size - y.size);
  if (shorter.size < 3) return false;
  let shared = 0;
  shorter.forEach((w) => {
    if (longer.has(w)) shared += 1;
  });
  return shared / shorter.size >= 0.8;
}

/** Steps in their original order without repeats; the first wording wins. */
export function dedupeSteps(steps: readonly string[]): string[] {
  const kept: string[] = [];
  for (const step of steps) {
    const text = stripNumbering(step);
    if (text && !kept.some((k) => isDuplicateStep(k, text))) kept.push(text);
  }
  return kept;
}

const RESTRICTION = /^(do not|don't|never|avoid|must not|should not)\b/i;

export type DiagnosisView = {
  problem: string;
  causes: string[];
  actions: string[];
  restrictions: string[];
};

/** Split a diagnosis into causes, ordered actions and separate safety restrictions. */
export function viewDiagnosis(d: {
  problem?: string;
  probable_causes?: string[];
  troubleshooting_steps?: string[];
}): DiagnosisView {
  const steps = dedupeSteps(d.troubleshooting_steps ?? []);
  return {
    problem: d.problem ?? "",
    causes: dedupeSteps(d.probable_causes ?? []),
    actions: steps.filter((s) => !RESTRICTION.test(s)),
    restrictions: steps.filter((s) => RESTRICTION.test(s)),
  };
}
