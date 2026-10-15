import { duration } from "../format";
import { useRefreshingQuery } from "../hooks";
import { StatsQuery } from "../operations";

export function StatsStrip({ refreshKey }: { refreshKey: number }) {
  const [{ data, error }, reexecute] = useRefreshingQuery({ query: StatsQuery }, refreshKey);

  if (error) {
    return (
      <div className="stats stats-error" role="alert">
        Couldn’t load the summary. <button onClick={() => reexecute({ requestPolicy: "network-only" })}>Try again</button>
      </div>
    );
  }

  const s = data?.stats;
  return (
    <section className="stats" aria-label="Summary" aria-busy={!s}>
      <div className="stat stat-open">
        <strong>{s ? s.openTotal : "–"}</strong>
        <span>open now</span>
      </div>
      <ul className="stat-sev">
        {(s?.openBySeverity ?? []).map((row) => (
          <li key={row.severity}>
            <i className={`dot sev-${row.severity.toLowerCase()}`} />
            <b>{row.count}</b> Sev {row.severity.slice(3)}
          </li>
        ))}
      </ul>
      <div className="stat">
        <strong>{s?.meanMinutesToResolve != null ? duration(s.meanMinutesToResolve) : "–"}</strong>
        <span>mean time to resolve, last 30 days</span>
      </div>
      <div className="stat">
        <strong>{s ? s.resolvedLast30Days : "–"}</strong>
        <span>resolved in the last 30 days</span>
      </div>
    </section>
  );
}
