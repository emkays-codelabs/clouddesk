"use client";

import Link from "next/link";
import { useState } from "react";
import { ApprovalDiff } from "@/components/tickets/ApprovalDiff";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { canAct, useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

/** The approval queue (docs/02_PRD.md FR-33): every action waiting for a person, with what it would do. */
export default function ApprovalsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState("pending");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const { data, error, loading, refresh } = usePolling(() => api.approvals(status), [status], {
    intervalMs: 5000,
  });

  async function decide(id: string, verb: "approve" | "reject") {
    setBusy(id);
    setMessage(null);
    try {
      await (verb === "approve" ? api.approve(id) : api.reject(id));
      setMessage(verb === "approve" ? "Approved. The action ran once." : "Rejected. The ticket was escalated.");
      await refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Approvals</h1>
      <select
        aria-label="Status"
        className="mb-4 rounded border border-slate-300 px-2 py-1 text-sm"
        value={status}
        onChange={(e) => setStatus(e.target.value)}
      >
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
      </select>
      {message ? (
        <p role="status" className="mb-3 rounded bg-slate-100 p-2 text-sm">
          {message}
        </p>
      ) : null}
      <DataState loading={loading} error={error} hasData={!!data}>
        {data && data.length === 0 ? (
          <EmptyState
            title={status === "pending" ? "Nothing is waiting" : "No approvals"}
            description="Refunds and setting resets wait here for a person."
          />
        ) : (
          <div className="space-y-4">
            {data?.map((a) => (
              <Card key={a.id}>
                <div className="mb-2 flex items-center justify-between text-sm">
                  <Link className="font-medium hover:underline" href={`/tickets/${a.ticket_id}`}>
                    {a.ticket_number}
                  </Link>
                  <span className="text-slate-500">
                    {a.status} · {formatDate(a.created_at)}
                  </span>
                </div>
                <ApprovalDiff action={a.action} riskLevel={a.risk_level} reason={a.reason} />
                {a.status === "pending" ? (
                  <div className="mt-3 flex gap-2">
                    <Button disabled={!canAct(user) || busy === a.id} onClick={() => void decide(a.id, "approve")}>
                      Approve
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={!canAct(user) || busy === a.id}
                      onClick={() => void decide(a.id, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-slate-500">
                    Decided by {a.decided_by ?? "-"}
                    {a.decision_note ? `: ${a.decision_note}` : ""}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </DataState>
    </div>
  );
}
