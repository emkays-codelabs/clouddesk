"use client";

import { useState } from "react";
import { DataState } from "@/components/ui/DataState";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { humanize } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

type Hit = { id: string; title: string; snippet: string; score: number };

export default function KnowledgePage() {
  const { data, error, loading } = usePolling(() => api.articles(), []);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  async function search() {
    setSearchError(null);
    try {
      setHits((await api.searchKnowledge(query)).results);
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : "Search failed.");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Knowledge</h1>
      <Card title="Search the knowledge base">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <input
            aria-label="Search query"
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="For example: locked out after MFA attempts"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Button type="submit" disabled={!query.trim()}>
            Search
          </Button>
        </form>
        {searchError ? <p role="alert" className="mt-2 text-sm text-red-700">{searchError}</p> : null}
        {hits ? (
          <ol className="mt-3 space-y-2 text-sm">
            {hits.map((h) => (
              <li key={h.id}>
                <span className="font-medium">{h.title}</span> <span className="text-slate-500">({h.score.toFixed(2)})</span>
                <div className="text-slate-600">{h.snippet}</div>
              </li>
            ))}
          </ol>
        ) : null}
      </Card>
      <DataState loading={loading} error={error} hasData={!!data}>
        <Card title="Articles">
          <ul className="divide-y divide-slate-100 text-sm">
            {data?.map((a) => (
              <li key={a.id} className="py-2">
                <span className="font-medium">{a.title}</span>{" "}
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{humanize(a.category)}</span>
                <div className="text-slate-600">{a.summary}</div>
              </li>
            ))}
          </ul>
        </Card>
      </DataState>
    </div>
  );
}
