interface Props {
  label?: string;
  // Düğme içinde kullanım: yalnızca dönen gösterge, etiket yok.
  inline?: boolean;
}

export default function Spinner({ label = "Yükleniyor…", inline }: Props) {
  if (inline) return <span className="spinner spinner-inline" aria-hidden="true" />;
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
