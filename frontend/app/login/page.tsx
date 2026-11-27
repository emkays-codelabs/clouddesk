"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/lib/auth";

const DEMO_USERS = [
  { email: "sam.agent@clouddesk.demo", label: "Sam (agent)", note: "runs, approves, replies" },
  { email: "admin@clouddesk.demo", label: "Admin", note: "everything, plus reindex" },
  { email: "vic.viewer@clouddesk.demo", label: "Vic (viewer)", note: "read only" },
];

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const expired = useSearchParams().get("reason") === "expired";
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function signIn(email: string) {
    setBusy(email);
    setError(null);
    try {
      await login(email);
      router.replace("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed.");
      setBusy(null);
    }
  }

  return (
    <Card title="Sign in to CloudDesk" className="w-full max-w-sm">
      {expired ? (
        <p role="status" className="mb-3 rounded bg-amber-50 p-2 text-sm text-amber-900">
          Your session expired. Please sign in again.
        </p>
      ) : null}
      <p className="mb-3 text-sm text-slate-600">Choose a demo user.</p>
      <ul className="space-y-2">
        {DEMO_USERS.map((u) => (
          <li key={u.email}>
            <Button
              variant="secondary"
              className="w-full text-left"
              disabled={busy !== null}
              onClick={() => signIn(u.email)}
            >
              <span className="font-medium">{u.label}</span>
              <span className="block text-xs text-slate-500">{u.note}</span>
            </Button>
          </li>
        ))}
      </ul>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </Card>
  );
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gradient-to-br from-brand-50 via-white to-sand-100 p-6">
      <div className="flex items-center gap-3 text-2xl font-extrabold tracking-tight text-brand-900">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-teal-500 shadow-soft">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 17.5 12 4l7 13.5M8 13h8M7 17.5h10" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        CloudDesk
      </div>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
      <Link href="/" className="text-sm font-medium text-brand-700 hover:underline">
        ← Back to home
      </Link>
    </main>
  );
}
