// Yükleme sırasında kart ızgarası yer tutucusu (yalnızca sunum).
export default function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div className="card skeleton-card" key={i}>
          <div className="skeleton skeleton-media" />
          <div className="card-body">
            <div className="skeleton skeleton-line skeleton-line-lg" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line skeleton-line-sm" />
          </div>
        </div>
      ))}
    </div>
  );
}
