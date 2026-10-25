import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";

interface PublicJob {
  id: string;
  title: string;
  company: string;
  department: string;
  location: string;
  employment_type: string;
  experience_min: number;
  experience_max: number;
  description: string;
  created_at: string;
}

export default function PublicJobs() {
  const [jobs, setJobs] = useState<PublicJob[] | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [applying, setApplying] = useState<PublicJob | null>(null);
  const [cover, setCover] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const { me, isCandidate, isRecruiter } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    api.get<PublicJob[]>("/public/jobs").then(setJobs).catch(() => setJobs([]));
  }, []);

  async function submitApplication() {
    if (!applying) return;
    if (!isCandidate) {
      push("info", "Please sign in with a candidate account to apply.");
      navigate("/login");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("job_id", applying.id);
      fd.append("cover_letter", cover);
      if (file) fd.append("file", file);
      const res = await api.postForm<{ application_id: string; stage: string }>("/me/apply", fd);
      push("success", "Application submitted. You can track it in your dashboard.");
      setApplying(null);
      setCover("");
      setFile(null);
      navigate("/candidate");
      void res;
    } catch (e: any) {
      push("error", e.message || "Could not submit application");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
      <Badge tone="blue">Careers</Badge>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Open roles</h1>
      <p className="mt-3 text-slate-600">
        Roles published by organizations on TalentLens. Sign in as a candidate to apply with your resume.
      </p>

      {isRecruiter && (
        <div className="mt-4 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-800">
          You're signed in as a recruiter. These are public postings across the platform.
        </div>
      )}

      <div className="mt-10 space-y-4">
        {jobs === null && [1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
        {jobs?.length === 0 && (
          <EmptyState title="No open roles yet" message="When organizations publish jobs, they'll appear here." />
        )}
        {jobs?.map((j) => (
          <Card key={j.id} className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{j.title}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {[j.company, j.department, j.location].filter(Boolean).join(" · ")}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge>{j.employment_type.replace("_", " ")}</Badge>
                  {(j.experience_min || j.experience_max) && (
                    <Badge tone="blue">{j.experience_min}–{j.experience_max} yrs</Badge>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn-secondary" onClick={() => setExpanded(expanded === j.id ? null : j.id)}>
                  {expanded === j.id ? "Hide" : "View"}
                </button>
                <button className="btn-primary" onClick={() => (me ? setApplying(j) : navigate("/login"))}>
                  Apply
                </button>
              </div>
            </div>
            {expanded === j.id && (
              <p className="mt-4 whitespace-pre-wrap border-t border-slate-100 pt-4 text-sm text-slate-600">
                {j.description}
              </p>
            )}
          </Card>
        ))}
      </div>

      {applying && (
        <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setApplying(null)} />
          <div className="relative z-50 w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Apply · {applying.title}</h3>
            <p className="mt-1 text-sm text-slate-500">Upload a PDF or DOCX resume (max 15 MB).</p>
            <div className="mt-4 space-y-3">
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="input file:mr-3 file:rounded file:border-0 file:bg-brand-50 file:px-3 file:py-1 file:text-brand-700"
              />
              <textarea
                className="input"
                rows={4}
                placeholder="Cover note (optional)"
                value={cover}
                onChange={(e) => setCover(e.target.value)}
              />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setApplying(null)}>Cancel</button>
              <button className="btn-primary" onClick={submitApplication} disabled={busy}>
                {busy ? "Submitting…" : "Submit application"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
