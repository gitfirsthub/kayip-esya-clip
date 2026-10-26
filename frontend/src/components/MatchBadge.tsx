import type { MatchLevel } from "../types";

const CLASS: Record<MatchLevel, string> = {
  "yüksek": "badge-high",
  orta: "badge-mid",
  "düşük": "badge-low",
};

const TEXT: Record<MatchLevel, string> = {
  "yüksek": "Yüksek eşleşme",
  orta: "Orta eşleşme",
  "düşük": "Düşük eşleşme",
};

export default function MatchBadge({ level }: { level: MatchLevel }) {
  return <span className={`badge ${CLASS[level]}`}>{TEXT[level]}</span>;
}
