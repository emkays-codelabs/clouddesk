"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { ScrollToTop } from "@/components/ui/ScrollToTop";
import { Spinner } from "@/components/ui/Spinner";
import { Sidebar } from "./Sidebar";

/** The signed-in frame: sidebar, a header with who you are, and a redirect to /login without a session. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, ready, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Signing in" />
      </div>
    );
  }
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-sand-200 bg-white/75 px-6 py-3 text-sm backdrop-blur">
          <Link href="/" className="font-semibold text-brand-700 transition hover:-translate-x-0.5">
            ← Home
          </Link>
          <span className="ml-auto flex items-center gap-2 font-medium">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-teal-500 text-xs font-bold text-white">
              {user.full_name.slice(0, 1)}
            </span>
            {user.full_name}{" "}
            <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700">{user.role}</span>
          </span>
          <Button variant="secondary" onClick={logout}>
            Sign out
          </Button>
        </header>
        <main className="flex-1 p-6">{children}</main>
        <ScrollToTop />
      </div>
    </div>
  );
}
