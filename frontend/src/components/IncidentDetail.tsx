import { type FormEvent, useState } from "react";
import { useMutation } from "urql";
import { clock, duration, STATUS_LABEL, STATUS_STEPS } from "../format";
import type { Status } from "../gql/graphql";
import { useRefreshingQuery } from "../hooks";
import { IncidentQuery, PostUpdateMutation } from "../operations";
import { SeverityBadge, StatusTrack } from "./Badges";

interface Props {
  id: string;
  refreshKey: number;
  onClose: () => void;
}

export function IncidentDetail({ id, refreshKey, onClose }: Props) {
  const [{ data, fetching, error }] = useRefreshingQuery({ query: IncidentQuery, variables: { id } }, refreshKey);
  const incident = data?.incident;

  return (
    <aside className="detail" aria-label="Incident detail">
      <button className="close" onClick={onClose} aria-label="Close incident detail">Close</button>
      {error && <p role="alert">Couldn’t load this incident. {error.message}</p>}
      {!incident && fetching && <p aria-busy>Loading…</p>}
      {data && !incident && <p>This incident no longer exists.</p>}
      {incident && (
        <>
          <header>
            <SeverityBadge severity={incident.severity} />
            <h2>{incident.title}</h2>
            <p className="muted">
              {incident.service.name} is owned by {incident.service.ownerTeam} (tier {incident.service.tier}). Opened {clock(incident.createdAt)}
              {incident.resolvedAt ? `, resolved after ${duration(incident.durationMinutes)}.` : `, open for ${duration(incident.durationMinutes)}.`}
            </p>
            <StatusTrack status={incident.status} />
          </header>

          {incident.status === "RESOLVED" ? (
            <p className="notice-inline">This incident is resolved. Open a new one if it recurs.</p>
          ) : (
            <UpdateForm incidentId={incident.id} current={incident.status} />
          )}

          <ol className="timeline">
            {[...incident.updates].reverse().map((u) => (
              <li key={u.id}>
                <div className="tl-head">
                  <b>{STATUS_LABEL[u.status]}</b>
                  <time dateTime={u.createdAt}>{clock(u.createdAt)}</time>
                </div>
                <p>{u.message}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </aside>
  );
}

function UpdateForm({ incidentId, current }: { incidentId: string; current: Status }) {
  const [status, setStatus] = useState<Status>(current);
  const [message, setMessage] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [{ fetching }, postUpdate] = useMutation(PostUpdateMutation);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setProblem(null);
    const { data, error } = await postUpdate({ input: { incidentId, status, message } });
    if (error) return setProblem("Couldn’t reach the server. Your update wasn’t posted.");
    // Union result: expected failures arrive as data, narrowed by __typename.
    if (data?.postUpdate.__typename === "UserError") return setProblem(data.postUpdate.message);
    setMessage("");
  }

  return (
    <form className="update-form" onSubmit={submit}>
      <label>
        Status
        <select value={status} onChange={(e) => setStatus(e.target.value as Status)}>
          {STATUS_STEPS.map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
      </label>
      <label>
        Update for the timeline
        <textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="What changed, and what happens next?" />
      </label>
      {problem && <p className="error" role="alert">{problem}</p>}
      <button className="primary" disabled={fetching}>{fetching ? "Posting…" : "Post update"}</button>
    </form>
  );
}
