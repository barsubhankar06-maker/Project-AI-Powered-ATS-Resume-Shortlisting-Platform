import { useRef, useState } from "react";
import { orgStore, tokenStore } from "../lib/api";
import { Badge, Card, useToast } from "./ui";

interface UploadResult {
  filename: string;
  status?: string;
  resume_id?: string;
  duplicate?: boolean;
  error?: string;
}

export default function ResumeUploader({ jobId, onDone }: { jobId?: string; onDone?: () => void }) {
  const { push } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [results, setResults] = useState<UploadResult[] | null>(null);

  function upload(files: FileList | null) {
    if (!files || files.length === 0) return;
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("files", f));
    if (jobId) fd.append("job_id", jobId);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/resumes/upload");
    const token = tokenStore.get();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    const org = orgStore.get();
    if (org) xhr.setRequestHeader("X-Org-Id", org);

    setProgress(0);
    setResults(null);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      setProgress(null);
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 400) {
          push("error", body.detail || "Upload failed");
          setResults([{ filename: "-", error: body.detail || "Upload failed" }]);
          return;
        }
        setResults(body.results);
        const dupes = body.results.filter((r: UploadResult) => r.duplicate).length;
        const errs = body.results.filter((r: UploadResult) => r.error).length;
        push(
          errs ? "info" : "success",
          `Uploaded ${body.results.length} file(s)${dupes ? `, ${dupes} duplicate(s) linked` : ""}${errs ? `, ${errs} rejected` : ""}.`
        );
        onDone?.();
      } catch {
        push("error", "Unexpected response from server");
      }
    };
    xhr.onerror = () => {
      setProgress(null);
      push("error", "Network error during upload");
    };
    xhr.send(fd);
  }

  return (
    <Card className="p-5">
      <h2 className="mb-3 font-semibold text-slate-800">Upload resumes</h2>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files);
        }}
        className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
          dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-slate-50"
        }`}
      >
        <p className="text-sm text-slate-600">
          Drag & drop PDF or DOCX files here, or{" "}
          <button className="font-medium text-brand-600 underline" onClick={() => inputRef.current?.click()}>
            browse
          </button>
        </p>
        <p className="mt-1 text-xs text-slate-400">Up to 50 files per batch · max 10 MB each · duplicates are detected automatically</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => upload(e.target.files)}
        />
      </div>

      {progress !== null && (
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-slate-500">
            <span>Uploading…</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {results && (
        <ul className="mt-4 space-y-1 text-sm">
          {results.map((r, i) => (
            <li key={i} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2">
              <span className="truncate text-slate-700">{r.filename}</span>
              {r.error ? (
                <Badge tone="red">{r.error}</Badge>
              ) : r.duplicate ? (
                <Badge tone="amber">duplicate — linked</Badge>
              ) : (
                <Badge tone="green">queued</Badge>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-slate-400">
        Files are stored privately. Parsing runs in the background; refresh to see updated statuses.
      </p>
    </Card>
  );
}
