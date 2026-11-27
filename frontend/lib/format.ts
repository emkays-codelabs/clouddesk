/** "waiting_on_approval" -> "waiting on approval". */
export function humanize(value: string | null | undefined): string {
  return (value ?? "").replaceAll("_", " ");
}

/** A short local date and time, or a dash when there is no value. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function truncate(text: string, limit = 80): string {
  return text.length <= limit ? text : `${text.slice(0, limit - 1)}…`;
}

/** Display rate only: INR per USD. A converted amount is always shown next to the USD one. */
export const USD_TO_INR = Number(process.env.NEXT_PUBLIC_USD_INR ?? "85");

/** "$0.0123 / ₹1.0455": a model cost in USD and INR, always together. */
export function formatCost(usd: number): string {
  const rupees = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(usd * USD_TO_INR);
  return `$${usd.toFixed(4)} / ${rupees}`;
}

/**
 * The cost with how far to trust it: "Cost unavailable" when tokens were used but no price is
 * verified (never $0), "Actual" when the provider reported it, "Estimated" when it comes from a
 * configured price, and a dash when no model was called.
 */
export function describeCost(
  usd: number,
  basis: "none" | "actual" | "estimated" | "unavailable" | undefined,
): { label: string; text: string } {
  switch (basis) {
    case "unavailable":
      return { label: "Cost", text: "Cost unavailable" };
    case "actual":
      return { label: "Actual cost", text: formatCost(usd) };
    case "estimated":
      return { label: "Est. cost", text: formatCost(usd) };
    default:
      return { label: "Cost", text: "-" };
  }
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
}
