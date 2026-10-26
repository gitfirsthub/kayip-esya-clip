import { useEffect, useId, useRef, useState } from "react";
import { validateImage } from "../api";

interface Props {
  label: string;
  file: File | null;
  maxMb: number;
  required?: boolean;
  disabled?: boolean;
  onChange: (file: File | null) => void;
  onError: (message: string | null) => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImagePicker({
  label,
  file,
  maxMb,
  required,
  disabled,
  onChange,
  onError,
}: Props) {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Hem dosya seçici hem sürükle-bırak aynı doğrulama yolunu kullanır.
  function handle(picked: File | null) {
    if (!picked) {
      onChange(null);
      onError(null);
      return;
    }
    const problem = validateImage(picked, maxMb);
    if (problem) {
      if (inputRef.current) inputRef.current.value = "";
      onChange(null);
      onError(problem);
      return;
    }
    onError(null);
    onChange(picked);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    handle(e.dataTransfer.files?.[0] ?? null);
  }

  function remove() {
    if (inputRef.current) inputRef.current.value = "";
    handle(null);
  }

  return (
    <div className="field">
      <span className="label-text" id={`${id}-label`}>
        {label}
      </span>
      {preview && file ? (
        <div className="preview-card">
          <img
            className="preview"
            src={preview}
            alt={`Seçilen fotoğraf önizlemesi: ${file.name}`}
          />
          <div className="preview-info">
            <span className="preview-name">{file.name}</span>
            <span className="hint">{formatSize(file.size)}</span>
            <button className="btn btn-secondary" type="button" disabled={disabled} onClick={remove}>
              Kaldır
            </button>
          </div>
        </div>
      ) : (
        <div
          className={dragging ? "dropzone dropzone-active" : "dropzone"}
          data-disabled={disabled ? "true" : undefined}
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <svg width="40" height="40" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path
              d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="dropzone-title">Fotoğrafı buraya sürükleyin</span>
          <span className="dropzone-sub">veya seçmek için dokunun</span>
          <input
            ref={inputRef}
            id={id}
            className="dropzone-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            required={required && !file}
            disabled={disabled}
            aria-labelledby={`${id}-label`}
            aria-describedby={`${id}-hint`}
            onChange={(e) => handle(e.target.files?.[0] ?? null)}
          />
        </div>
      )}
      <span className="hint" id={`${id}-hint`}>
        JPEG, PNG veya WebP; en fazla {maxMb} MB.
      </span>
    </div>
  );
}
