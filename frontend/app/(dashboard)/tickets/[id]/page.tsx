"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ActionCard } from "@/components/tickets/ActionCard";
import { ApprovalDiff } from "@/components/tickets/ApprovalDiff";
import { EvidencePanel } from "@/components/tickets/EvidencePanel";
import { TicketTimeline } from "@/components/tickets/TicketTimeline";
import { WorkflowSteps } from "@/components/tickets/WorkflowSteps";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import { canAct, useAuth } from "@/lib/auth";
import { formatDate, humanize } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { WorkflowState } from "@/lib/types";

const FINISHED = ["completed", "escalated", "failed"];

function Chip({ children }: { children: string }) {
  return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{children}</span>;
}

export default function TicketPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user } = useAuth();
  const act = canAct(user);
  const ticket = usePolling(() => api.ticket(id), [id]);
  // Poll the workflow every 2 s until the run finishes (it also stops while the tab is hidden).
  const workflow = usePolling<WorkflowState | null>(
    () => api.workflow(id).catch((e) => (e?.status === 404 ? null : Promise.reject(e))),
    [id],
    { intervalMs: 2000, stopWhen: (w) => !!w && FINISHED.includes(w.status) },
  );
  const events = usePolling(() => api.events(id), [id, workflow.data?.status, workflow.data?.completed_nodes?.length], {
    intervalMs: 2000,
    stopWhen: () => !!workflow.data && FINISHED.includes(workflow.data.status),
  });
  const approval = usePolling(
    async () => {
      if (workflow.data?.approval_status !== "pending") return null;
      const pendingList = await api.approvals("pending");
      return pendingList.find((a) => a.id === workflow.data?.approval_request_id) ?? null;
    },
    [workflow.data?.approval_status, workflow.data?.approval_request_id],
  );
  const [reply, setReply] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const state = workflow.data;

  useEffect(() => {
    if (state?.final_response && reply === "") setReply(state.final_response);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.final_response]);

  useEffect(() => {
    if (state) void ticket.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.status]);

  async function guarded(action: () => Promise<unknown>, done: string) {
    setBusy(true);
    setNote(null);
    try {
      await action();
      setNote(done);
      await Promise.all([ticket.refresh(), workflow.refresh()]);
    } catch (e) {
      setNote(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  const t = ticket.data;
  const pending = state?.approval_status === "pending" && !!state.approval_request_id;
  return (
    <div>
      <Link href="/tickets" className="text-sm text-slate-600 hover:underline">
        ← Tickets
      </Link>
      <DataState loading={ticket.loading} error={ticket.error} hasData={!!t}>
        {t ? (
          <div className="mt-2 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold">
                {t.ticket_number} · {t.subject}
              </h1>
              <StatusPill status={t.status} />
              {t.severity ? <Chip>{t.severity}</Chip> : null}
            </div>
            {note ? (
              <p role="status" className="rounded bg-slate-100 p-2 text-sm">
                {note}
              </p>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-4">
                <Card title="Conversation">
                  <ul className="space-y-3 text-sm">
                    {t.messages.map((m) => (
                      <li key={m.id} className={m.internal ? "rounded bg-amber-50 p-2" : ""}>
                        <div className="text-xs text-slate-500">
                          {m.author_name || m.role} · {m.role}
                          {m.internal ? " · internal" : ""} · {formatDate(m.created_at)}
                        </div>
                        <div className="whitespace-pre-wrap">{m.body}</div>
                      </li>
                    ))}
                  </ul>
                </Card>
                <Card title="Reply">
                  <label className="sr-only" htmlFor="reply">
                    Reply
                  </label>
                  <textarea
                    id="reply"
                    className="h-32 w-full rounded border border-slate-300 p-2 text-sm"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Write a reply, or run the workflow for a draft"
                  />
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      disabled={!act || busy || !reply.trim()}
                      onClick={() => guarded(() => api.reply(id, reply), "Reply sent.")}
                    >
                      Send reply
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={!act || busy}
                      onClick={() =>
                        guarded(
                          () => api.requestInfo(id, ["Could you share more detail about the problem?"]),
                          "Asked the customer for more information.",
                        )
                      }
                    >
                      Request info
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={!act || busy}
                      onClick={() => guarded(() => api.escalate(id, "Escalated by an agent."), "Escalated.")}
                    >
                      Escalate
                    </Button>
                  </div>
                  {!act ? <p className="mt-2 text-xs text-slate-500">You can read this ticket but not act on it.</p> : null}
                </Card>
              </div>

              <Card title="Customer">
                <div className="space-y-2 text-sm">
                  <div className="font-medium">
                    <Link className="hover:underline" href={`/customers/${t.customer.id}`}>
                      {t.customer.name}
                    </Link>
                  </div>
                  <div>
                    {t.customer.company} · {t.customer.plan_name}
                  </div>
                  {t.subscription ? (
                    <div>
                      {t.subscription.seats} seats · {t.subscription.status} · storage {t.subscription.storage_used_gb}/
                      {t.subscription.storage_quota_gb} GB
                    </div>
                  ) : null}
                  <div className="pt-2 font-medium">Earlier tickets</div>
                  {t.history.length === 0 ? (
                    <div className="text-slate-500">None.</div>
                  ) : (
                    <ul className="list-disc pl-5">
                      {t.history.map((h) => (
                        <li key={h.id}>
                          <Link className="hover:underline" href={`/tickets/${h.id}`}>
                            {h.ticket_number}
                          </Link>{" "}
                          {h.subject}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </Card>

              <Card title="AI workflow">
                <div className="space-y-3 text-sm">
                  <Button
                    disabled={!act || busy || state?.status === "running" || t.status === "waiting_on_approval"}
                    onClick={() => guarded(() => api.runWorkflow(id), "Workflow started.")}
                  >
                    {state ? "Run again" : "Run AI workflow"}
                  </Button>
                  <WorkflowSteps state={state} />
                  {state?.classification ? (
                    <div className="flex flex-wrap gap-2">
                      <Chip>{humanize(state.classification.category)}</Chip>
                      {state.severity ? <Chip>{`severity ${state.severity}`}</Chip> : null}
                      {state.risk ? <RiskBadge level={state.risk.level} /> : null}
                      <Chip>{`${state.token_usage.total_tokens} tokens`}</Chip>
                    </div>
                  ) : null}
                  {state?.escalation_required ? (
                    <p className="rounded bg-red-50 p-2 text-red-800">Escalated: {state.escalation_reason}</p>
                  ) : null}
                  {pending && state ? (
                    <div className="rounded border border-amber-300 bg-amber-50 p-3">
                      <div className="mb-2 font-medium">Waiting for your approval</div>
                      {approval.data ? (
                        <ApprovalDiff
                          action={approval.data.action}
                          riskLevel={approval.data.risk_level}
                          reason={approval.data.reason}
                        />
                      ) : (
                        state.resolution_plan?.actions
                          .filter((a) => a.requires_approval)
                          .map((a) => <div key={a.tool}>{a.description}</div>)
                      )}
                      <div className="mt-2 flex gap-2">
                        <Button
                          disabled={!act || busy}
                          onClick={() => guarded(() => api.approve(state.approval_request_id!), "Approved. Running the action.")}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={!act || busy}
                          onClick={() => guarded(() => api.reject(state.approval_request_id!), "Rejected. Escalating.")}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  ) : null}
                  {state?.retrieved_docs.length ? (
                    <div>
                      <div className="mb-1 font-medium">Evidence</div>
                      <EvidencePanel evidence={state.retrieved_docs} />
                    </div>
                  ) : null}
                  {state?.diagnosis ? (
                    <div>
                      <div className="font-medium">Diagnosis</div>
                      <p>{state.diagnosis.problem}</p>
                      <ol className="list-decimal pl-5">
                        {state.diagnosis.troubleshooting_steps.map((s) => (
                          <li key={s}>{s.replace(/^\d+[.)]\s*/, "")}</li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                  {state?.actions.length ? (
                    <div className="space-y-2">
                      <div className="font-medium">Actions</div>
                      {state.actions.map((a) => (
                        <ActionCard
                          key={a.id}
                          action={{ tool: a.tool, requires_approval: a.requires_approval }}
                          status={a.status}
                        />
                      ))}
                    </div>
                  ) : null}
                  <div>
                    <div className="mb-1 font-medium">Timeline</div>
                    <TicketTimeline events={events.data ?? []} />
                  </div>
                  {state?.errors.length ? (
                    <p role="alert" className="text-red-700">
                      {state.errors.join("; ")}
                    </p>
                  ) : null}
                </div>
              </Card>
            </div>
          </div>
        ) : null}
      </DataState>
    </div>
  );
}
