import { useState } from "react";
import { Buoy, Scenario, launchAttack } from "../api/client";

interface Props {
  buoys: Buoy[];
  scenarios: Record<string, Scenario>;
}

export default function AttackConsole({ buoys, scenarios }: Props) {
  const [target, setTarget] = useState("SS-B01");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const fire = async (scenario: string) => {
    setBusy(true);
    try {
      setMsg({ ok: true, text: await launchAttack(scenario, target) });
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
      window.setTimeout(() => setMsg(null), 5000);
    }
  };

  const waveBuoys = buoys.filter((b) => b.sensors.includes("wave_height_m"));

  return (
    <section className="card console">
      <header>
        <h2>Attack console <span className="tag tag-sim">SIMULATION</span></h2>
        <p className="muted">
          Try to fool the network. Attacks are injected into the live stream and judged by the
          same engine as real data.
        </p>
      </header>
      <label className="target">
        Target buoy
        <select value={target} onChange={(e) => setTarget(e.target.value)}>
          {(waveBuoys.length ? waveBuoys : buoys).map((b) => (
            <option key={b.buoy_id} value={b.buoy_id}>
              {b.buoy_id} {b.name}
            </option>
          ))}
        </select>
      </label>
      <div className="attack-grid">
        {Object.entries(scenarios).map(([id, s]) => (
          <button key={id} className="attack" disabled={busy} onClick={() => fire(id)}>
            <strong>{s.title}</strong>
            <span>{s.what}</span>
            <em>{s.threat}</em>
          </button>
        ))}
      </div>
      {msg && <p className={msg.ok ? "toast ok" : "toast err"}>{msg.text}</p>}
    </section>
  );
}
