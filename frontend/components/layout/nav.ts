export type NavItem = { href: string; label: string };

/** The one place navigation is declared; the sidebar renders this list. */
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/tickets", label: "Tickets" },
  { href: "/approvals", label: "Approvals" },
  { href: "/customers", label: "Customers" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/escalations", label: "Escalations" },
  { href: "/agents", label: "Agents" },
  { href: "/audit", label: "Audit" },
  { href: "/settings", label: "Settings" },
];
