import { useEffect, useId, useState } from "react";
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
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handle(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0] ?? null;
    if (!picked) {
      onChange(null);
      onError(null);
      return;
    }
    const problem = validateImage(picked, maxMb);
    if (problem) {
      e.target.value = "";
      onChange(null);
      onError(problem);
      return;
    }
    onError(null);
    onChange(picked);
  }

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        required={required}
        disabled={disabled}
        onChange={handle}
      />
      <span className="hint">JPEG, PNG veya WebP; en fazla {maxMb} MB.</span>
      {preview && file && (
        <img className="preview" src={preview} alt={`Seçilen fotoğraf önizlemesi: ${file.name}`} />
      )}
    </div>
  );
}
