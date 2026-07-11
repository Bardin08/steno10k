import { useRef, useState } from "react";
import { UploadSimple } from "@phosphor-icons/react";
import { toast } from "../../components";

const SUPPORTED = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".mp4", ".mov", ".webm"];
const MAX_BYTES = 1024 ** 3; // 1 GB
const MAX_FILES = 10;

function extOf(name: string) {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i).toLowerCase();
}

function validate(files: File[]): { ok: File[]; error?: string } {
  if (files.length > MAX_FILES) return { ok: [], error: `Up to ${MAX_FILES} files at a time.` };
  for (const f of files) {
    if (!SUPPORTED.includes(extOf(f.name))) return { ok: [], error: `Unsupported file: ${f.name}` };
    if (f.size > MAX_BYTES) return { ok: [], error: `${f.name} is over 1 GB.` };
  }
  return { ok: files };
}

export function UploadZone({ onFiles, disabled }: { onFiles: (files: File[]) => void; disabled?: boolean }) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function accept(list: FileList | null) {
    if (!list || list.length === 0) return;
    const { ok, error } = validate(Array.from(list));
    if (error) { toast.error(error); return; }
    onFiles(ok);
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); accept(e.dataTransfer.files); }}
      onClick={() => input.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); }
      }}
      className={`flex cursor-pointer flex-col items-center gap-2 rounded-md border border-dashed px-6 py-10 text-center transition-colors ${
        over ? "border-ink bg-surface" : "border-hairline-strong"
      } ${disabled ? "pointer-events-none opacity-50" : ""}`}
    >
      <UploadSimple size={24} className="text-ink-faint" weight="duotone" />
      <p className="text-sm text-ink-soft">Drop up to {MAX_FILES} audio files, or click to choose</p>
      <input
        ref={input}
        type="file"
        multiple
        accept={SUPPORTED.join(",")}
        className="hidden"
        onChange={(e) => { accept(e.target.files); e.target.value = ""; }}
      />
    </div>
  );
}
