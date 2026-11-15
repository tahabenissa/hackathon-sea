import type { LiveEvent, Stats } from "../api/client";

const SS_LABEL: Record<string, string> = {
  ISSUED: "Warning issued (verified data)",
  HELD: "Alert held: data implausible",
  BLOCKED: "Blocked: forged message",
  ESCALATED: "Escalated: possible hidden danger",
  REVIEW: "Suspicious reading sent for review",
};

function time(e: LiveEvent) {
  return e.observed_at ? e.observed_at.replace("T", " ").slice(0, 16) : "";
}

export default function Centres({ events, stats }: { events: LiveEvent[]; stats: Stats }) {
  const unprotected = events.filter((e) => e.unprotected_alert).slice(-6).reverse();
  const seashield = events.filter((e) => e.seashield_alert).slice(-6).reverse();
  const fake = stats.fake_alerts_unprotected ?? 0;

  return (
    <div className="centres">
      <section className="card centre centre-bad">
        <header>
          <h2>Unprotected centre</h2>
          <p className="muted">Trusts every message. Alerts when waves exceed 6 m.</p>
        </header>
        <div className="kpis">
          <div><span className="kpi">{stats.unprotected_alerts ?? 0}</span>alerts raised</div>
          <div><span className="kpi kpi-bad">{fake}</span>caused by attacks</div>
        </div>
        <ul className="alerts">
          {unprotected.length === 0 && <li className="muted">No alerts yet</li>}
          {unprotected.map((e) => (
            <li key={`${e.buoy_id}-${e.seq}-${e.received_at}`} className={e.simulated_attack ? "fake" : ""}>
              <strong>🚨 DISASTER ALERT</strong> {e.buoy_id} · {e.data.wave_height_m?.toFixed(1)} m waves
              <span className="muted"> · {time(e)}</span>
              {e.simulated_attack && <span className="tag tag-bad">FAKE: {e.simulated_attack} attack</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="card centre centre-good">
        <header>
          <h2>SeaShield AI centre</h2>
          <p className="muted">Verifies every message before it can raise or silence an alert.</p>
        </header>
        <div className="kpis">
          <div><span className="kpi">{stats.seashield_ISSUED ?? 0}</span>verified warnings</div>
          <div><span className="kpi kpi-good">{stats.attacks_caught ?? 0}</span>attacks caught</div>
          <div><span className="kpi">{stats.attacks_launched ?? 0}</span>attacks launched</div>
        </div>
        <ul className="alerts">
          {seashield.length === 0 && <li className="muted">Nothing to report yet</li>}
          {seashield.map((e) => (
            <li key={`${e.buoy_id}-${e.seq}-${e.received_at}`} className={`ss-${e.seashield_alert?.toLowerCase()}`}>
              <strong>{SS_LABEL[e.seashield_alert ?? ""] ?? e.seashield_alert}</strong> {e.buoy_id}
              <span className="muted"> · {time(e)}</span>
              <div className="why">{e.explanation}</div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
