"use client";

import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { ActionCard } from "@/components/tickets/ActionCard";
import { ApprovalDiff } from "@/components/tickets/ApprovalDiff";
import { DiagnosisPanel } from "@/components/tickets/DiagnosisPanel";
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

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function Chip({ children }: { children: string }) {
  return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">{children}</span>;
}

export default function TicketPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user } = useAuth();
  const act = canAct(user);
  const ticket = usePolling(() => api.ticket(id), [id]);
  // Poll the workflow every 2 s until the run finishes (it also stops while the tab is hidden).
  // After "Run", keep polling until the NEW run shows up and ends; otherwise a stale finished state
  // from the previous run would stop the polling and leave the button enabled.
  const [expectedRun, setExpectedRun] = useState<string | null>(null);
  const workflow = usePolling<WorkflowState | null>(
    () => api.workflow(id).catch((e) => (e?.status === 404 ? null : Promise.reject(e))),
    [id],
    {
      intervalMs: 2000,
      stopWhen: (w) =>
        !!w && FINISHED.includes(w.status) && (expectedRun === null || w.workflow_id === expectedRun),
    },
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
  const replyBox = useRef<HTMLTextAreaElement>(null);
  const state = workflow.data;

  useEffect(() => {
    if (state?.final_response && reply === "") setReply(state.final_response);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.final_response]);

  // Grow the reply box with its text, up to a maximum; beyond that it scrolls.
  useEffect(() => {
    const el = replyBox.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 150), 320)}px`;
  }, [reply]);

  useEffect(() => {
    if (state) void ticket.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.status]);

  async function startRun() {
    setBusy(true);
    setNote(null);
    try {
      const run = await api.runWorkflow(id);
      setExpectedRun(run.workflow_id);
      setNote("Workflow started.");
      await sleep(400);
      await Promise.all([ticket.refresh(), workflow.refresh()]);
    } catch (e) {
      setNote(e instanceof Error ? e.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

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
  const runStale = expectedRun !== null && state?.workflow_id !== expectedRun;
  const running = state?.status === "running" || runStale;
  const runLabel = running ? "Workflow running…" : state ? "Run workflow again" : "Run AI workflow";
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
            <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr_1.4fr]">
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
                    ref={replyBox}
                    rows={6}
                    className="min-h-[150px] max-h-80 w-full resize-none rounded-xl border border-sand-200 bg-white p-3 text-sm"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Write a reply, or run the workflow for a draft"
                  />
                  <div className="mt-3 flex flex-wrap gap-2 [&>button]:whitespace-nowrap [&>button]:px-3">
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
                <div className="space-y-3 text-sm">
                  <div className="text-base font-semibold">
                    <Link className="hover:underline" href={`/customers/${t.customer.id}`}>
                      {t.customer.name}
                    </Link>
                  </div>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-xl bg-sand-50 p-2">
                      <dt className="text-slate-500">Company</dt>
                      <dd className="font-semibold">{t.customer.company}</dd>
                    </div>
                    <div className="rounded-xl bg-sand-50 p-2">
                      <dt className="text-slate-500">Plan</dt>
                      <dd className="font-semibold capitalize">{t.customer.plan_name}</dd>
                    </div>
                    {t.subscription ? (
                      <>
                        <div className="rounded-xl bg-sand-50 p-2">
                          <dt className="text-slate-500">Account status</dt>
                          <dd>
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold capitalize text-emerald-800">
                              {t.subscription.status}
                            </span>
                          </dd>
                        </div>
                        <div className="rounded-xl bg-sand-50 p-2">
                          <dt className="text-slate-500">Seats</dt>
                          <dd className="font-semibold">{t.subscription.seats}</dd>
                        </div>
                        <div className="col-span-2 rounded-xl bg-sand-50 p-2">
                          <dt className="text-slate-500">Storage</dt>
                          <dd className="font-semibold">
                            {t.subscription.storage_used_gb} / {t.subscription.storage_quota_gb} GB
                          </dd>
                        </div>
                      </>
                    ) : null}
                  </dl>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-xl bg-sand-50 p-2">
                      <dt className="text-slate-500">Customer since</dt>
                      <dd className="font-semibold">{formatDate(t.customer.created_at)}</dd>
                    </div>
                    {t.customer.region ? (
                      <div className="rounded-xl bg-sand-50 p-2">
                        <dt className="text-slate-500">Region</dt>
                        <dd className="font-semibold">{t.customer.region}</dd>
                      </div>
                    ) : null}
                    <div className="col-span-2 rounded-xl bg-sand-50 p-2">
                      <dt className="text-slate-500">Customer ID</dt>
                      <dd className="break-all font-mono text-[11px]">{t.customer.id}</dd>
                    </div>
                  </dl>
                  <div className="pt-2 font-medium">Earlier tickets ({t.history.length})</div>
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

              <Card title="AI workflow" className="lg:self-start">
                <div className="space-y-4 text-sm">
                  <section aria-label="Workflow status" className="sticky top-16 z-10 -mx-5 -mt-1 space-y-3 border-b border-sand-200 bg-white/95 px-5 pb-3 pt-1 backdrop-blur">
                    <Button
                      disabled={!act || busy || running || t.status === "waiting_on_approval"}
                      onClick={() => void startRun()}
                    >
                      {runLabel}
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
                  </section>

                  {pending && state ? (
                    <section aria-label="Approval" className="rounded-xl border border-amber-300 bg-amber-50 p-3">
                      <div className="mb-2 font-semibold">Waiting for your approval</div>
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
                      <div className="mt-3 flex gap-2">
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
                    </section>
                  ) : null}

                  {state?.escalation_required ? (
                    <section aria-label="Escalation" className="rounded-xl border border-rose-300 bg-rose-50 p-3 text-rose-900">
                      <div className="font-semibold">Escalated to a person</div>
                      <p>Escalated: {state.escalation_reason}</p>
                    </section>
                  ) : null}

                  {state?.retrieved_docs.length || state?.completed_nodes.includes("knowledge_retrieval") ? (
                    <details open className="group">
                      <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-slate-500">
                        Evidence ({state?.retrieved_docs.length ?? 0})
                      </summary>
                      <div className="mt-2">
                        <EvidencePanel evidence={state?.retrieved_docs ?? []} />
                      </div>
                    </details>
                  ) : null}

                  {state?.diagnosis ? (
                    <details open>
                      <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-slate-500">
                        Diagnosis and recommended actions
                      </summary>
                      <div className="mt-2">
                        <DiagnosisPanel diagnosis={state.diagnosis} />
                      </div>
                    </details>
                  ) : null}

                  {state?.actions.length ? (
                    <details open>
                      <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-slate-500">
                        Actions ({state.actions.length})
                      </summary>
                      <div className="mt-2 space-y-2">
                        {state.actions.map((a) => (
                          <ActionCard
                            key={a.id}
                            action={{ tool: a.tool, requires_approval: a.requires_approval }}
                            status={a.status}
                          />
                        ))}
                      </div>
                    </details>
                  ) : null}

                  {state?.ticket_summary ? (
                    <details open>
                      <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-slate-500">
                        Summary
                      </summary>
                      <p className="mt-2 whitespace-pre-wrap text-slate-700">{state.ticket_summary}</p>
                      {state.completed_nodes.includes("memory_update") ? (
                        <p className="mt-1 text-xs text-slate-500">Safe customer notes were saved for next time.</p>
                      ) : null}
                    </details>
                  ) : null}

                  <details>
                    <summary className="cursor-pointer text-xs font-bold uppercase tracking-wider text-slate-500">
                      Timeline ({events.data?.length ?? 0} events)
                    </summary>
                    <div className="mt-2">
                      <TicketTimeline events={events.data ?? []} />
                    </div>
                  </details>

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
