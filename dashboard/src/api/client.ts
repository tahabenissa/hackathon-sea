// Thin client for the FastAPI backend + live WebSocket.

export type Verdict =
  | "TRUSTED"
  | "REJECTED"
  | "SUSPECTED_FDI"
  | "CONFIRMED_EVENT"
  | "SUPPRESSED_WARNING";

export interface Evidence {
  layer: "crypto" | "physics" | "anomaly" | "spatial";
  passed: boolean;
  score: number | null;
  detail: string;
}

export interface Assessment {
  buoy_id: string;
  seq: number;
  verdict: Verdict;
  risk: number;
  evidence: Evidence[];
  explanation: string;
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export function connectLive(onAssessment: (a: Assessment) => void): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/live`);
  ws.onmessage = (e) => onAssessment(JSON.parse(e.data) as Assessment);
  return ws;
}
