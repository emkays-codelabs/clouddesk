import { EmptyState } from "./EmptyState";

export function PagePlaceholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">{title}</h1>
      <EmptyState title={`${title} is not built yet`} description="This page arrives in a later task." />
    </div>
  );
}
