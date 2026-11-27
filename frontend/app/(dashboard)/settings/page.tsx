"use client";

import { formatMoney } from "@/lib/format";
import { DataState } from "@/components/ui/DataState";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1 text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const { data, error, loading } = usePolling(() => api.settings(), []);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Settings</h1>
      <p className="mb-4 text-sm text-slate-600">Read only. Change them in the backend environment.</p>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Runtime">
              <Row label="Environment" value={data.environment} />
              <Row label="Demo mode" value={data.demo_mode ? "on" : "off"} />
              <Row label="Database" value={data.database} />
              <Row label="Vector store" value={data.vector_store} />
            </Card>
            <Card title="Language model">
              <Row label="Provider" value={data.llm.llm_provider} />
              <Row label="Model" value={data.llm.llm_model || "default"} />
              <Row label="API key" value={data.llm.api_key_configured ? "configured" : "not set"} />
            </Card>
            <Card title="Approval policy">
              <Row label="Refunds need approval" value={data.approval_policy.refunds_require_approval ? "yes" : "no"} />
              <Row label="Refund allowed without approval up to" value={formatMoney(data.approval_policy.max_refund_without_approval)} />
            </Card>
          </div>
        ) : null}
      </DataState>
    </div>
  );
}
