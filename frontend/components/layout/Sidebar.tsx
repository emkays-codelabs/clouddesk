"use client";

import {
  Activity,
  BookOpen,
  CheckCircle2,
  LayoutDashboard,
  ScrollText,
  Settings,
  Siren,
  Ticket,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./nav";

const ICONS: Record<string, LucideIcon> = {
  "/dashboard": LayoutDashboard,
  "/tickets": Ticket,
  "/approvals": CheckCircle2,
  "/customers": UserRound,
  "/knowledge": BookOpen,
  "/escalations": Siren,
  "/agents": Activity,
  "/audit": ScrollText,
  "/settings": Settings,
};

export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-gradient-to-b from-brand-900 to-[#0e5a45] p-4 text-emerald-50 md:flex"
    >
      <Link href="/" className="mb-8 flex items-center gap-3 text-lg font-extrabold tracking-tight" aria-label="CloudDesk home">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/15">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 17.5 12 4l7 13.5M8 13h8M7 17.5h10" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        CloudDesk
      </Link>
      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = ICONS[item.href] ?? LayoutDashboard;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition duration-200 ${
                  active ? "bg-white text-brand-700 shadow-soft" : "text-emerald-100/90 hover:translate-x-1 hover:bg-white/10"
                }`}
              >
                <Icon size={17} aria-hidden="true" />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
      <p className="mt-auto px-2 text-[11px] leading-relaxed text-emerald-100/60">
        Human-controlled decisions. Every action is recorded.
      </p>
    </nav>
  );
}
