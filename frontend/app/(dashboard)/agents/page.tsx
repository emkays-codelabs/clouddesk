"use client";

import { DataState } from "@/components/ui/DataState";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { formatCost } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

export default function AgentsPage() {
  const { data, error, loading } = usePolling(() => api.agents(), [], { intervalMs: 10000 });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Agents</h1>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data ? (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 text-sm">
              <Card title="Runs">{data.stats.runs_total}</Card>
              <Card title="Failed">{data.stats.runs_failed}</Card>
              <Card title="Tokens">{data.stats.total_tokens}</Card>
              <Card title="Est. cost">{formatCost(data.stats.total_estimated_cost_usd)}</Card>
            </div>
            <Card title="The six agents">
              <ul className="divide-y divide-slate-100 text-sm">
                {data.agents.map((a) => (
                  <li key={a.name} className="py-2">
                    <span className="font-medium">{a.name}</span>{" "}
                    <span className="text-slate-500">({a.role}, {a.runs} runs)</span>
                    <div className="text-slate-600">{a.description}</div>
                    {a.tools.length ? <div className="text-xs text-slate-500">tools: {a.tools.join(", ")}</div> : null}
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="The graph">
              <ol className="list-decimal pl-5 text-sm">
                {data.graph.nodes.map((n) => (
                  <li key={n.id}>{n.label}</li>
                ))}
              </ol>
            </Card>
          </>
        ) : null}
      </DataState>
    </div>
  );
}
