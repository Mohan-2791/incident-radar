import { useEffect, useMemo, useState } from "react";
import { useSubscription } from "urql";
import { IncidentDetail } from "./components/IncidentDetail";
import { IncidentList } from "./components/IncidentList";
import { NewIncidentDialog } from "./components/NewIncidentDialog";
import { ServiceList } from "./components/ServiceList";
import { StatsStrip } from "./components/StatsStrip";
import { onLiveStatus } from "./client";
import { SEVERITY_LABEL, STATUS_LABEL } from "./format";
import type { IncidentFilter, Severity } from "./gql/graphql";
import { IncidentChangedSubscription } from "./operations";

type View = "open" | "resolved" | "all";
const VIEWS: { id: View; label: string }[] = [
  { id: "open", label: "Open" },
  { id: "resolved", label: "Resolved" },
  { id: "all", label: "All" },
];

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export function App() {
  const [view, setView] = useState<View>("open");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search.trim(), 250);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  // Live updates: the server pushes `incidentChanged`; we bump a key that makes every
  // visible query refetch, and flash a one-line note about what changed.
  const [refreshKey, setRefreshKey] = useState(0);
  const [live, setLive] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [{ data: event }] = useSubscription({ query: IncidentChangedSubscription });

  useEffect(() => onLiveStatus(setLive), []);
  useEffect(() => {
    if (!event) return;
    setRefreshKey((k) => k + 1);
    setNote(`${event.incidentChanged.title}: ${STATUS_LABEL[event.incidentChanged.status].toLowerCase()}`);
    const t = setTimeout(() => setNote(null), 6000);
    return () => clearTimeout(t);
  }, [event]);

  useEffect(() => {
    if (!selectedId) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !creating && setSelectedId(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, creating]);

  const filter = useMemo<IncidentFilter>(
    () => ({
      status: view === "open" ? ["INVESTIGATING", "IDENTIFIED", "MONITORING"] : view === "resolved" ? ["RESOLVED"] : undefined,
      severity: severity ? [severity] : undefined,
      serviceId: serviceId ?? undefined,
      search: debouncedSearch || undefined,
    }),
    [view, severity, serviceId, debouncedSearch],
  );

  const clearFilters = () => {
    setView("all");
    setSeverity("");
    setServiceId(null);
    setSearch("");
  };

  return (
    <div className={selectedId ? "app has-detail" : "app"}>
      <header className="top">
        <h1>Incident Radar</h1>
        <p className={live ? "live up" : "live"} role="status">
          <i className="dot" />
          {live ? "Live" : "Connecting"}
          {note && <span className="note">{note}</span>}
        </p>
        <button className="primary" onClick={() => setCreating(true)}>Open incident</button>
      </header>

      <StatsStrip refreshKey={refreshKey} />

      <div className="body">
        <ServiceList selected={serviceId} onSelect={setServiceId} refreshKey={refreshKey} />

        <main>
          <div className="filters">
            <div className="seg" role="group" aria-label="Status">
              {VIEWS.map((v) => (
                <button key={v.id} className={view === v.id ? "on" : ""} aria-pressed={view === v.id} onClick={() => setView(v.id)}>
                  {v.label}
                </button>
              ))}
            </div>
            <label className="inline">
              <span className="sr">Severity</span>
              <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")}>
                <option value="">Any severity</option>
                {(Object.keys(SEVERITY_LABEL) as Severity[]).map((s) => (
                  <option key={s} value={s}>{SEVERITY_LABEL[s]}</option>
                ))}
              </select>
            </label>
            <label className="inline grow">
              <span className="sr">Search titles</span>
              <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search titles" />
            </label>
          </div>

          <IncidentList
            key={JSON.stringify(filter)}
            filter={filter}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onClearFilters={clearFilters}
            refreshKey={refreshKey}
          />
        </main>

        {selectedId && <IncidentDetail key={selectedId} id={selectedId} refreshKey={refreshKey} onClose={() => setSelectedId(null)} />}
      </div>

      <NewIncidentDialog
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(id) => {
          setCreating(false);
          setSelectedId(id);
          setView("open");
        }}
      />
    </div>
  );
}
