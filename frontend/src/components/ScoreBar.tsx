export default function ScoreBar({ score }: { score: number }) {
  const percent = Math.max(0, Math.min(100, Math.round(score * 100)));
  return (
    <div className="score">
      <div
        className="score-track"
        role="meter"
        aria-label="Benzerlik"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <div className="score-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="score-text">Benzerlik: %{percent}</span>
    </div>
  );
}
