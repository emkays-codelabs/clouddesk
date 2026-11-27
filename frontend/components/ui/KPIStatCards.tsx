export type Kpi = { label: string; value: string | number };

/** A row of headline numbers (docs/04_LLD.md 12.2). */
export function KPIStatCards({ items }: { items: readonly Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-2xl border border-sand-200 bg-white p-5 shadow-soft transition duration-200 hover:-translate-y-1 hover:shadow-lift"
        >
          <div className="bg-gradient-to-r from-brand-500 to-teal-500 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
            {item.value}
          </div>
          <div className="mt-1 text-xs font-semibold uppercase tracking-wider text-slate-500">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
