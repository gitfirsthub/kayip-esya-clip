import { useState } from "react";
import { imageSrc } from "../api";
import type { Item, MatchLevel } from "../types";
import MatchBadge from "./MatchBadge";
import ScoreBar from "./ScoreBar";

interface Props {
  item: Item;
  score?: number;
  level?: MatchLevel;
  showTags?: boolean;
}

function PinIcon() {
  return (
    <svg className="meta-icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 22s7-6.2 7-12a7 7 0 10-14 0c0 5.8 7 12 7 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.5" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg className="meta-icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="3" y="5" width="18" height="16" rx="2" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M3 10h18M8 3v4M16 3v4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function BoxIcon() {
  return (
    <svg className="meta-icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M3 7l9-4 9 4v10l-9 4-9-4V7zM3 7l9 4 9-4M12 11v10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function ItemCard({ item, score, level, showTags }: Props) {
  const [imgDone, setImgDone] = useState(false);
  const tags = item.tags ?? [];

  return (
    <article className="card item-card">
      <div className={imgDone ? "card-media" : "card-media skeleton"}>
        <img
          className="card-img"
          src={imageSrc(item)}
          alt={`${item.title} fotoğrafı`}
          loading="lazy"
          onLoad={() => setImgDone(true)}
          onError={() => setImgDone(true)}
        />
      </div>
      <div className="card-body">
        <h3>{item.title}</h3>
        {(level || item.status === "teslim_edildi") && (
          <div className="badges">
            {level && <MatchBadge level={level} />}
            {item.status === "teslim_edildi" && <span className="badge badge-low">Teslim edildi</span>}
          </div>
        )}
        {score !== undefined && <ScoreBar score={score} />}
        <ul className="meta">
          <li>
            <PinIcon />
            <span className="sr-only">Bulunduğu yer: </span>
            {item.location}
          </li>
          <li>
            <CalendarIcon />
            <span className="sr-only">Tarih: </span>
            {item.found_date}
          </li>
          <li>
            <BoxIcon />
            <span className="sr-only">Teslim noktası: </span>
            {item.dropoff_point}
          </li>
        </ul>
        {showTags && (
          <dl className="facts">
            <dt>Kategori</dt>
            <dd>{item.category}</dd>
            <dt>Renk</dt>
            <dd>{item.color}</dd>
            <dt>Yüz bulanıklaştırma</dt>
            <dd>
              {item.faces_blurred > 0
                ? `${item.faces_blurred} yüz bulanıklaştırıldı`
                : "Yüz bulunmadı"}
            </dd>
          </dl>
        )}
        {item.description && <p className="desc">{item.description}</p>}
        {(tags.length > 0 || item.redacted_regions > 0) && (
          <ul className="chips" aria-label="Etiketler">
            {tags.map((t) => (
              <li className="chip" key={t}>
                {t}
              </li>
            ))}
            {item.redacted_regions > 0 && (
              <li className="chip chip-info">{item.redacted_regions} bölge gizlendi</li>
            )}
          </ul>
        )}
        {item.document_like && (
          <p className="doc-note">Belge benzeri görsel: yazılar gizlendi</p>
        )}
      </div>
    </article>
  );
}
