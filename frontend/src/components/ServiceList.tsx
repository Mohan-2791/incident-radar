import { useRefreshingQuery } from "../hooks";
import { ServicesQuery } from "../operations";

interface Props {
  selected: string | null;
  onSelect: (serviceId: string | null) => void;
  refreshKey: number;
}

export function ServiceList({ selected, onSelect, refreshKey }: Props) {
  const [{ data, error }] = useRefreshingQuery({ query: ServicesQuery }, refreshKey);

  return (
    <nav className="services" aria-label="Services">
      <h2>Services</h2>
      {error && <p className="muted" role="alert">Couldn’t load services.</p>}
      <ul>
        <li>
          <button className={selected === null ? "svc active" : "svc"} onClick={() => onSelect(null)} aria-pressed={selected === null}>
            All services
          </button>
        </li>
        {data?.services.map((svc) => (
          <li key={svc.id}>
            <button
              className={selected === svc.id ? "svc active" : "svc"}
              onClick={() => onSelect(selected === svc.id ? null : svc.id)}
              aria-pressed={selected === svc.id}
            >
              <span className="svc-name">{svc.name}</span>
              <span className="svc-team">{svc.ownerTeam}</span>
              {svc.openIncidentCount > 0 && <span className="svc-count" aria-label={`${svc.openIncidentCount} open`}>{svc.openIncidentCount}</span>}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
