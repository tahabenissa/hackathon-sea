const LAYERS = [
  { n: 1, t: "Crypto gate", d: "Per-buoy HMAC signature, sequence number, timestamp and nonce. Stops tampering, fake devices and replays." },
  { n: 2, t: "Physics checks", d: "Limits learned from 3 years of real buoy data: impossible values, impossible jumps, waves without wind." },
  { n: 3, t: "AI anomaly score (advisory)", d: "An Isolation Forest per buoy, trained on real 2023 data, scores how unusual each reading is. Shown to the operator, never obeyed blindly: real hurricanes are unusual too." },
  { n: 4, t: "Neighbour check (next)", d: "Nearby buoys must tell a consistent story. A storm spreads across the network; a lie does not." },
];

export default function HowItWorks() {
  return (
    <section className="card how">
      <h2>How SeaShield decides</h2>
      <p className="muted">
        Ocean buoys feed disaster-warning centres, and those centres trust what they receive. A hacked buoy
        or an intercepted message can trigger a fake disaster alert, or hide a real storm. SeaShield checks
        every reading before it can raise or silence a warning. A human operator makes the final call
        on anything suspicious.
      </p>
      <ol className="layers">
        {LAYERS.map((l) => (
          <li key={l.n}>
            <span className="n">{l.n}</span>
            <strong>{l.t}</strong>
            <span>{l.d}</span>
          </li>
        ))}
      </ol>
      <p className="muted small">
        Data: NOAA National Data Buoy Center, stations 42036, 42097, 42099, 42013 (West Florida Shelf),
        replayed at 1 historical hour every 2 seconds, including real Hurricane Helene (Sept 2024).
        All attacks are simulated.
      </p>
    </section>
  );
}
