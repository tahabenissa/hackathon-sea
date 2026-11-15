// Thin client for the FastAPI backend + live WebSocket.

export type Verdict =
  | "TRUSTED"
  | "REJECTED"
  | "SUSPECTED_FDI"
  | "CONFIRMED_EVENT"
  | "SUPPRESSED_WARNING";

export type SeaShieldAlert = "ISSUED" | "HELD" | "BLOCKED" | "ESCALATED" | "REVIEW" | null;

export interface Evidence {
  layer: "crypto" | "physics" | "anomaly" | "spatial";
  passed: boolean;
  score: number | null;
  detail: string;
}

export interface Measurements {
  wave_height_m?: number | null;
  dominant_period_s?: number | null;
  wind_speed_ms?: number | null;
  wind_dir_deg?: number | null;
  pressure_hpa?: number | null;
  water_temp_c?: number | null;
}

export interface LiveEvent {
  buoy_id: string;
  seq: number;
  observed_at: string | null;
  received_at: string;
  data: Measurements;
  verdict: Verdict;
  risk: number;
  evidence: Evidence[];
  explanation: string;
  unprotected_alert: string | null;
  seashield_alert: SeaShieldAlert;
  simulated_attack: string | null;
}

export interface Buoy {
  buoy_id: string;
  name: string;
  ndbc_station: string | null;
  lat: number | null;
  lon: number | null;
  sensors: string[];
}

export interface Scenario {
  title: string;
  threat: string;
  what: string;
}

export type Stats = Record<string, number>;

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function launchAttack(scenario: string, buoyId: string): Promise<string> {
  const res = await fetch(`/api/attacks/${scenario}?buoy_id=${encodeURIComponent(buoyId)}`, {
    method: "POST",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ?? `HTTP ${res.status}`);
  return `Simulated attack sent to ${buoyId}`;
}

export function connectLive(onEvent: (e: LiveEvent) => void, onStatus: (up: boolean) => void): () => void {
  let ws: WebSocket | null = null;
  let stopped = false;
  let retry: number | undefined;

  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/live`);
    ws.onopen = () => onStatus(true);
    ws.onmessage = (m) => onEvent(JSON.parse(m.data) as LiveEvent);
    ws.onclose = () => {
      onStatus(false);
      if (!stopped) retry = window.setTimeout(open, 2000);
    };
  };
  open();
  return () => {
    stopped = true;
    window.clearTimeout(retry);
    ws?.close();
  };
}
