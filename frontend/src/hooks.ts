import { useEffect } from "react";
import { type AnyVariables, type UseQueryArgs, useQuery } from "urql";

/**
 * useQuery that also refetches (bypassing cache) whenever `refreshKey` changes.
 * The app bumps the key when the server pushes an `incidentChanged` event, so changes
 * made by *other* people show up without polling.
 */
export function useRefreshingQuery<Data, Variables extends AnyVariables>(
  args: UseQueryArgs<Variables, Data>,
  refreshKey: number,
) {
  const result = useQuery<Data, Variables>(args);
  const reexecute = result[1];
  useEffect(() => {
    if (refreshKey > 0) reexecute({ requestPolicy: "network-only" });
  }, [refreshKey, reexecute]);
  return result;
}
