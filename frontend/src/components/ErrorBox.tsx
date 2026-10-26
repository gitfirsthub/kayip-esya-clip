export default function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="error-box" role="alert">
      <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M12 7v6M12 16.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span>{message}</span>
    </div>
  );
}
