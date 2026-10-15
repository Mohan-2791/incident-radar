import { createClient as createWSClient } from "graphql-ws";
import { cacheExchange, Client, fetchExchange, subscriptionExchange } from "urql";

// Dev: relative "/graphql" (Vite proxies it). Prod: set VITE_API_URL=https://api.example.com/graphql
const HTTP_URL: string = import.meta.env.VITE_API_URL ?? "/graphql";
const WS_URL = HTTP_URL.startsWith("http")
  ? HTTP_URL.replace(/^http/, "ws")
  : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${HTTP_URL}`;

const wsClient = createWSClient({ url: WS_URL, retryAttempts: Infinity });

export const client = new Client({
  url: HTTP_URL,
  exchanges: [
    // Document cache: a mutation that returns IncidentType invalidates every cached query
    // containing that type, so lists and detail views refetch without manual cache surgery.
    cacheExchange,
    fetchExchange,
    subscriptionExchange({
      forwardSubscription(request) {
        const input = { ...request, query: request.query ?? "" };
        return {
          subscribe(sink) {
            const unsubscribe = wsClient.subscribe(input, sink);
            return { unsubscribe };
          },
        };
      },
    }),
  ],
});

export function onLiveStatus(listener: (connected: boolean) => void): () => void {
  const offUp = wsClient.on("connected", () => listener(true));
  const offDown = wsClient.on("closed", () => listener(false));
  return () => {
    offUp();
    offDown();
  };
}
