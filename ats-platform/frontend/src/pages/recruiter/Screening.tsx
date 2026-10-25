import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";
import CandidateTable from "../../components/CandidateTable";
import ResumeUploader from "../../components/ResumeUploader";

export default function Screening() {
  const { push } = useToast();
  const [jobs, setJobs] = useState<any[] | null>(null);
  const [jobId, setJobId] = useState("");
  const [resumes, setResumes] = useState<any[] | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    api.get<any[]>("/jobs").then((j) => {
      setJobs(j);
      if (j.length && !jobId) setJobId(j[0].id);
    }).catch((e) => push("error", e.message));
  }, [push]);

  useEffect(() => {
    if (!jobId) return;
    setResumes(null);
    api.get<any[]>(`/resumes?job_id=${jobId}`).then(setResumes).catch((e) => push("error", e.message));
  }, [jobId, refresh, push]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Resume Screening</h1>
          <p className="text-sm text-slate-500">Upload resumes, watch parsing status, and review ranked matches.</p>
        </div>
        <select className="input w-64" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          {jobs?.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </div>

      {jobs && jobs.length === 0 && (
        <EmptyState title="No jobs yet" message="Create a job first, then upload resumes against it." />
      )}

      {jobId && (
        <>
          <ResumeUploader jobId={jobId} onDone={() => setRefresh((r) => r + 1)} />

          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Processing status</h2>
              <button className="btn-secondary" onClick={() => setRefresh((r) => r + 1)}>Refresh</button>
            </div>
            {resumes === null ? (
              <Skeleton className="h-20 w-full" />
            ) : resumes.length === 0 ? (
              <p className="text-sm text-slate-400">No resumes uploaded for this job yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {resumes.map((r) => (
                  <li key={r.id} className="flex items-center justify-between gap-3 py-2">
                    <div className="min-w-0">
                      <div className="truncate text-slate-700">{r.filename}</div>
                      {r.error && <div className="text-xs text-rose-600">{r.error}</div>}
                    </div>
                    <div className="flex items-center gap-2">
                      {r.ocr_used && <Badge tone="blue">OCR</Badge>}
                      <Badge tone={r.status === "completed" ? "green" : r.status === "failed" ? "red" : "amber"}>{r.status}</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <div>
            <h2 className="mb-3 font-semibold text-slate-800">Ranked candidates</h2>
            <CandidateTable jobId={jobId} />
          </div>
        </>
      )}
    </div>
  );
}
