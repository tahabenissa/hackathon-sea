import { useEffect, useState } from "react";
import { Buoy, LiveEvent, Scenario, Stats, connectLive, getJson } from "./api/client";

const MAX_EVENTS = 300;

export function useLive() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [buoys, setBuoys] = useState<Buoy[]>([]);
  const [scenarios, setScenarios] = useState<Record<string, Scenario>>({});
  const [stats, setStats] = useState<Stats>({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    getJson<Buoy[]>("/buoys").then(setBuoys).catch(() => undefined);
    getJson<Record<string, Scenario>>("/attacks/scenarios").then(setScenarios).catch(() => undefined);
    getJson<LiveEvent[]>("/events").then((e) => setEvents(e.slice(-MAX_EVENTS))).catch(() => undefined);

    const stop = connectLive(
      (e) => setEvents((prev) => [...prev.slice(-(MAX_EVENTS - 1)), e]),
      setConnected,
    );
    const poll = window.setInterval(() => {
      getJson<Stats>("/stats").then(setStats).catch(() => undefined);
    }, 2000);
    getJson<Stats>("/stats").then(setStats).catch(() => undefined);
    return () => {
      stop();
      window.clearInterval(poll);
    };
  }, []);

  return { events, buoys, scenarios, stats, connected };
}
