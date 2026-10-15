import { useState } from "react";
import { duration, timeAgo } from "../format";
import type { IncidentFilter } from "../gql/graphql";
import { useRefreshingQuery } from "../hooks";
import { IncidentsQuery } from "../operations";
import { SeverityBadge, StatusTrack } from "./Badges";

interface Props {
  filter: IncidentFilter;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onClearFilters: () => void;
  refreshKey: number;
}

/**
 * Cursor pagination, urql style: one <Page> (one query) per cursor. "Load more" appends a page
 * instead of replacing data, and mutations/subscription events refetch every page.
 */
export function IncidentList(props: Props) {
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  return (
    <div className="list">
      {cursors.map((after, i) => (
        <Page
          key={after ?? "first"}
          {...props}
          after={after}
          isFirst={i === 0}
          isLast={i === cursors.length - 1}
          onLoadMore={(cursor) => setCursors((c) => [...c, cursor])}
        />
      ))}
    </div>
  );
}

interface PageProps extends Props {
  after: string | null;
  isFirst: boolean;
  isLast: boolean;
  onLoadMore: (cursor: string) => void;
}

function Page({ filter, after, isFirst, isLast, selectedId, onSelect, onClearFilters, onLoadMore, refreshKey }: PageProps) {
  const [{ data, fetching, error }, reexecute] = useRefreshingQuery({ query: IncidentsQuery, variables: { filter, after } }, refreshKey);

  if (error) {
    return (
      <div className="notice" role="alert">
        <p>Couldn’t load incidents. {error.networkError ? "The API isn’t reachable." : error.message}</p>
        <button onClick={() => reexecute({ requestPolicy: "network-only" })}>Try again</button>
      </div>
    );
  }
  if (!data) return isFirst ? <div className="notice" aria-busy>Loading incidents…</div> : <div className="notice" aria-busy>Loading more…</div>;

  const { edges, totalCount, pageInfo } = data.incidents;
  if (isFirst && edges.length === 0) {
    return (
      <div className="notice">
        <p>No incidents match these filters.</p>
        <button onClick={onClearFilters}>Clear filters</button>
      </div>
    );
  }

  return (
    <>
      {isFirst && <p className="count">{totalCount} {totalCount === 1 ? "incident" : "incidents"}</p>}
      <ul className="rows">
        {edges.map(({ node }) => (
          <li key={node.id}>
            <button className={`row spine-${node.severity.toLowerCase()}${selectedId === node.id ? " selected" : ""}`} onClick={() => onSelect(node.id)} aria-current={selectedId === node.id}>
              <span className="row-main">
                <span className="row-title">{node.title}</span>
                <span className="row-meta">
                  <SeverityBadge severity={node.severity} />
                  <span>{node.service.name}</span>
                  <span>opened {timeAgo(node.createdAt)}</span>
                  <span>{node.status === "RESOLVED" ? `lasted ${duration(node.durationMinutes)}` : `open for ${duration(node.durationMinutes)}`}</span>
                </span>
              </span>
              <StatusTrack status={node.status} />
            </button>
          </li>
        ))}
      </ul>
      {isLast && pageInfo.hasNextPage && pageInfo.endCursor && (
        <button className="more" disabled={fetching} onClick={() => onLoadMore(pageInfo.endCursor!)}>
          Load more
        </button>
      )}
    </>
  );
}
