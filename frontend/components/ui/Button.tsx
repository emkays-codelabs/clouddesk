import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" };

export function Button({ variant = "primary", className = "", ...rest }: Props) {
  const tone =
    variant === "primary"
      ? "bg-gradient-to-r from-brand-500 to-teal-500 text-white shadow-soft hover:-translate-y-0.5 hover:shadow-lift"
      : "border border-sand-200 bg-white text-slate-900 hover:border-brand-500 hover:bg-brand-50";
  return (
    <button
      className={`rounded-xl px-4 py-2 text-sm font-semibold transition duration-200 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 ${tone} ${className}`}
      {...rest}
    />
  );
}
