import { useState } from "react";

import { DebugResource, loadDebugResource } from "../api";

type AdminPanelProps = {
  userId: string;
};

type DebugState = Partial<Record<DebugResource, unknown>>;

const resources: { key: DebugResource; label: string }[] = [
  { key: "memories", label: "Load Memories" },
  { key: "people", label: "Load People" },
  { key: "events", label: "Load Events" },
];

export function AdminPanel({ userId }: AdminPanelProps) {
  const [debugData, setDebugData] = useState<DebugState>({});
  const [loadingResource, setLoadingResource] = useState<DebugResource | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLoad(resource: DebugResource) {
    setLoadingResource(resource);
    setError(null);

    try {
      const data = await loadDebugResource(userId, resource);
      setDebugData((currentData) => ({ ...currentData, [resource]: data }));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to load debug data.");
    } finally {
      setLoadingResource(null);
    }
  }

  return (
    <section className="admin-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Development only</p>
          <h2>Debug admin panel</h2>
        </div>
        <span className="status-pill">user: {userId.slice(0, 8)}</span>
      </div>

      <div className="admin-actions">
        {resources.map((resource) => (
          <button
            key={resource.key}
            type="button"
            onClick={() => handleLoad(resource.key)}
            disabled={loadingResource === resource.key}
          >
            {loadingResource === resource.key ? "Loading..." : resource.label}
          </button>
        ))}
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="json-blocks">
        {resources.map((resource) => (
          <details className="json-panel" key={resource.key}>
            <summary>{resource.key}</summary>
            <pre>
              {JSON.stringify(
                debugData[resource.key] ?? { hint: `Click ${resource.label}` },
                null,
                2,
              )}
            </pre>
          </details>
        ))}
      </div>
    </section>
  );
}
