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

/** Display rate only: INR per USD. Costs are estimates and are always shown in both currencies. */
export const USD_TO_INR = Number(process.env.NEXT_PUBLIC_USD_INR ?? "85");

/** "$0.0123 / ₹1.0455": an estimated model cost in USD and INR, always together. */
export function formatCost(usd: number): string {
  const rupees = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(usd * USD_TO_INR);
  return `$${usd.toFixed(4)} / ${rupees}`;
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
}
