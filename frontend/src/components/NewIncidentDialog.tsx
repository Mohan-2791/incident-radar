import { type FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "urql";
import { SEVERITY_LABEL } from "../format";
import type { Severity } from "../gql/graphql";
import { OpenIncidentMutation, ServicesQuery } from "../operations";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}

const SEVERITIES: Severity[] = ["SEV1", "SEV2", "SEV3"];

export function NewIncidentDialog({ open, onClose, onCreated }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [{ data }] = useQuery({ query: ServicesQuery, pause: !open });
  const [{ fetching }, openIncident] = useMutation(OpenIncidentMutation);
  const [serviceId, setServiceId] = useState("");
  const [severity, setSeverity] = useState<Severity>("SEV2");
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<{ field: string; message: string } | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!serviceId && data?.services[0]) setServiceId(data.services[0].id);
  }, [data, serviceId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await openIncident({ input: { serviceId, severity, title, message } });
    if (res.error) return setError({ field: "form", message: "Couldn’t reach the server. Nothing was created." });
    const payload = res.data?.openIncident;
    if (payload?.__typename === "UserError") return setError({ field: payload.field, message: payload.message });
    if (payload?.__typename === "IncidentType") {
      setTitle("");
      setMessage("");
      onCreated(payload.id);
    }
  }

  const fieldError = (field: string) =>
    error && (error.field === field || (field === "title" && error.field === "form")) ? <p className="error" role="alert">{error.message}</p> : null;

  return (
    <dialog ref={ref} className="dialog" onClose={onClose}>
      <form onSubmit={submit}>
        <h2>Open an incident</h2>
        <label>
          Service
          <select value={serviceId} onChange={(e) => setServiceId(e.target.value)}>
            {data?.services.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
        {fieldError("serviceId")}
        <fieldset>
          <legend>Severity</legend>
          {SEVERITIES.map((s) => (
            <label key={s} className={`choice sev-${s.toLowerCase()}`}>
              <input type="radio" name="severity" checked={severity === s} onChange={() => setSeverity(s)} />
              {SEVERITY_LABEL[s]}
            </label>
          ))}
        </fieldset>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={140} placeholder="Elevated 5xx on payment confirmation" />
        </label>
        {fieldError("title")}
        <label>
          What are you seeing?
          <textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} />
        </label>
        {fieldError("message")}
        <div className="dialog-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={fetching}>{fetching ? "Opening…" : "Open incident"}</button>
        </div>
      </form>
    </dialog>
  );
}
