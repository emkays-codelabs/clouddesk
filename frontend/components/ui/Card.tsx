import type { ReactNode } from "react";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-sand-200 bg-white p-5 shadow-soft transition duration-200 hover:shadow-lift ${className}`}
    >
      {title ? (
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold tracking-tight text-brand-900">
          <span aria-hidden="true" className="h-4 w-1 rounded-full bg-gradient-to-b from-brand-500 to-teal-400" />
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  );
}
