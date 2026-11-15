import { useMemo } from "react";
import type { LiveEvent } from "./api/client";
import AttackConsole from "./components/AttackConsole";
import BuoyMap from "./components/BuoyMap";
import Centres from "./components/Centres";
import EventFeed from "./components/EventFeed";
import HowItWorks from "./components/HowItWorks";
import WaveChart from "./components/WaveChart";
import { useLive } from "./useLive";

const HOUR = 3_600_000;

export default function App() {
  const { events, buoys, scenarios, stats, connected } = useLive();

  const { latest, offline, clock } = useMemo(() => {
    const latest: Record<string, LiveEvent> = {};
    let clock = 0;
    for (const e of events) {
      if (e.simulated_attack) continue;
      latest[e.buoy_id] = e;
      clock = Math.max(clock, e.observed_at ? Date.parse(e.observed_at) : 0);
    }
    const offline = new Set(
      buoys
        .map((b) => b.buoy_id)
        .filter((id) => !latest[id] || Date.parse(latest[id].observed_at ?? "") < clock - 1.5 * HOUR),
    );
    return { latest, offline, clock };
  }, [events, buoys]);

  const waveBuoys = buoys.filter((b) => b.sensors.includes("wave_height_m")).map((b) => b.buoy_id);
  const clockText = clock ? new Date(clock).toISOString().replace("T", " ").slice(0, 16) + " UTC" : "waiting for data…";

  return (
    <div className="page">
      <header className="top">
        <div className="brand">
          <span className="logo">🛡️</span>
          <div>
            <h1>SeaShield <span>AI</span></h1>
            <p>Intelligent cybersecurity for ocean monitoring</p>
          </div>
        </div>
        <div className="status">
          <span className={`dot ${connected ? "on" : "off"}`} />
          {connected ? "Live" : "Reconnecting…"}
          <span className="clock">Sea time: {clockText}</span>
          <span className="tag tag-sim">Real NOAA data · simulated attacks</span>
        </div>
      </header>

      <main className="grid-main">
        <section className="card map-card">
          <h2>Buoy network · West Florida Shelf</h2>
          <BuoyMap buoys={buoys} latest={latest} offline={offline} />
          <p className="muted small">
            Green = trusted · amber = suspicious · red = rejected · grey = offline (storms knock real buoys offline)
          </p>
        </section>
        <AttackConsole buoys={buoys} scenarios={scenarios} />
      </main>

      <Centres events={events} stats={stats} />
      <WaveChart events={events} waveBuoys={waveBuoys} />
      <EventFeed events={events} />
      <HowItWorks />

      <footer className="muted small">
        SeaShield AI · HackGlobal 2026 · Civic and real-world impact ·{" "}
        <a href="https://github.com/tahabenissa/hackathon-sea">source code</a>
      </footer>
    </div>
  );
}
