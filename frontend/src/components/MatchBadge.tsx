import type { MatchLevel } from "../types";

const CLASS: Record<MatchLevel, string> = {
  "yüksek": "badge-high",
  orta: "badge-mid",
  "düşük": "badge-low",
};

export default function MatchBadge({ level }: { level: MatchLevel }) {
  return <span className={`badge ${CLASS[level]}`}>Eşleşme: {level}</span>;
}
