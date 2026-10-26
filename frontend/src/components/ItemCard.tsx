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

export default function ItemCard({ item, score, level, showTags }: Props) {
  return (
    <article className="card">
      <img
        className="card-img"
        src={imageSrc(item)}
        alt={`${item.title} fotoğrafı`}
        loading="lazy"
      />
      <div className="card-body">
        <h3>{item.title}</h3>
        {level && <MatchBadge level={level} />}
        {score !== undefined && <ScoreBar score={score} />}
        {item.status === "teslim_edildi" && <span className="badge badge-low">Teslim edildi</span>}
        <dl className="facts">
          <dt>Bulunduğu yer</dt>
          <dd>{item.location}</dd>
          <dt>Tarih</dt>
          <dd>{item.found_date}</dd>
          <dt>Teslim noktası</dt>
          <dd>{item.dropoff_point}</dd>
          {showTags && (
            <>
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
            </>
          )}
        </dl>
        {item.description && <p className="desc">{item.description}</p>}
      </div>
    </article>
  );
}
