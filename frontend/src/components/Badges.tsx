import { SEVERITY_LABEL, STATUS_LABEL, STATUS_STEPS } from "../format";
import type { Severity, Status } from "../gql/graphql";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`sev sev-${severity.toLowerCase()}`}>{SEVERITY_LABEL[severity]}</span>;
}

/** Four segments = the four stages an incident moves through, so position is information. */
export function StatusTrack({ status }: { status: Status }) {
  const reached = STATUS_STEPS.indexOf(status);
  return (
    <span className="track" role="img" aria-label={`Status: ${STATUS_LABEL[status]}`}>
      <span className="track-bars" aria-hidden>
        {STATUS_STEPS.map((step, i) => (
          <i key={step} className={i <= reached ? (status === "RESOLVED" ? "done" : "on") : ""} />
        ))}
      </span>
      <span className="track-label">{STATUS_LABEL[status]}</span>
    </span>
  );
}
