import { useEffect, useState } from "react";
import { getJson } from "../api/client";

export default function Overview() {
  const [health, setHealth] = useState<string>("checking…");

  useEffect(() => {
    getJson<{ status: string; version: string }>("/health")
      .then((h) => setHealth(`${h.status} (v${h.version})`))
      .catch(() => setHealth("API unreachable"));
  }, []);

  return (
    <section>
      <h1>Network overview</h1>
      <p className="muted">Intelligent cybersecurity for ocean monitoring.</p>
      <div className="grid">
        <div className="card"><h3>API</h3><p>{health}</p></div>
        <div className="card"><h3>Buoys trusted</h3><p>n/a</p></div>
        <div className="card"><h3>Open incidents</h3><p>n/a</p></div>
        <div className="card"><h3>Alerts held vs issued</h3><p>n/a</p></div>
      </div>
    </section>
  );
}
