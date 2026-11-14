import type { Verdict } from "../api/client";

const LABELS: Record<Verdict, string> = {
  TRUSTED: "Trusted",
  REJECTED: "Rejected",
  SUSPECTED_FDI: "Suspected FDI",
  CONFIRMED_EVENT: "Confirmed event",
  SUPPRESSED_WARNING: "Possible hidden danger",
};

export default function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span className={`badge badge-${verdict.toLowerCase()}`}>{LABELS[verdict]}</span>;
}
