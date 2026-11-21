import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" };

export function Button({ variant = "primary", className = "", ...rest }: Props) {
  const tone =
    variant === "primary"
      ? "bg-slate-900 text-white hover:bg-slate-700"
      : "border border-slate-300 bg-white text-slate-900 hover:bg-slate-100";
  return (
    <button
      className={`rounded px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${tone} ${className}`}
      {...rest}
    />
  );
}
