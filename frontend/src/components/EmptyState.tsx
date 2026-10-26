import type { ReactNode } from "react";

interface Props {
  title: string;
  children?: ReactNode;
}

export default function EmptyState({ title, children }: Props) {
  return (
    <div className="empty-state">
      <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
        <rect x="10" y="18" width="44" height="32" rx="6" fill="none" stroke="currentColor" strokeWidth="3" />
        <path d="M10 28h44" stroke="currentColor" strokeWidth="3" />
        <circle cx="32" cy="39" r="5" fill="none" stroke="currentColor" strokeWidth="3" />
        <path d="M24 12h16" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <p className="empty-title">{title}</p>
      {children && <p className="empty-text">{children}</p>}
    </div>
  );
}
