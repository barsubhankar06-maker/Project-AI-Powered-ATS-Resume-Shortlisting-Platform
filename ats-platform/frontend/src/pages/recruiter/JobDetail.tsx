import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";
import { Requirement, RequirementsEditor, WeightsEditor } from "../../components/RequirementsEditor";
import CandidateTable from "../../components/CandidateTable";
import ResumeUploader from "../../components/ResumeUploader";

export default function JobDetail() {
  const { jobId = "" } = useParams();
  const { push } = useToast();
  const [job, setJob] = useState<any>(null);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [tab, setTab] = useState<"candidates" | "requirements" | "settings">("candidates");
  const [saving, setSaving] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    const data = await api.get<any>(`/jobs/${jobId}`);
    setJob(data);
    setRequirements(data.requirements || []);
    setWeights(data.weights || {});
  }, [jobId]);

  useEffect(() => {
    load().catch((e) => push("error", e.message));
  }, [load, push]);

  async function saveRequirements() {
    setSaving(true);
    try {
      await api.post(`/jobs/${jobId}/requirements`, requirements);
      push("success", "Requirements saved — existing scores marked stale until re-run.");
      setRefreshKey((k) => k + 1);
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setSaving(false);
    }
  }

  async function saveSettings() {
    const total = Object.values(weights).reduce((a, b) => a + Number(b || 0), 0);
    if (Math.abs(total - 100) > 0.01) {
      push("error", "Weights must total 100%");
      return;
    }
    setSaving(true);
    try {
      await api.patch(`/jobs/${jobId}`, {
        weights,
        status: job.status,
        blind_screening: job.blind_screening,
        feedback_enabled: job.feedback_enabled,
        experience_min: job.experience_min,
        experience_max: job.experience_max,
      });
      push("success", "Job settings saved");
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!job) return <div className="space-y-4"><Skeleton className="h-10 w-1/3" /><Skeleton className="h-64 w-full" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/app/jobs" className="text-sm text-brand-600 hover:underline">← All jobs</Link>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">{job.title}</h1>
          <p className="text-sm text-slate-500">
            {[job.company, job.department, job.location].filter(Boolean).join(" · ")}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone={job.status === "open" ? "green" : "slate"}>{job.status}</Badge>
            <Badge tone="slate">v{job.version}</Badge>
            {(job.experience_min || job.experience_max) && <Badge tone="blue">{job.experience_min}–{job.experience_max} yrs</Badge>}
            {job.blind_screening && <Badge tone="brand">blind screening</Badge>}
          </div>
        </div>
        <Link to={`/app/jobs/${jobId}/pipeline`} className="btn-secondary">View pipeline</Link>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {([["candidates", "Candidates"], ["requirements", "Requirements"], ["settings", "Settings"]] as const).map(([k, l]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === k ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === "candidates" && (
        <div className="space-y-6">
          <ResumeUploader jobId={jobId} onDone={() => setRefreshKey((k) => k + 1)} />
          <div key={refreshKey}>
            <CandidateTable jobId={jobId} />
          </div>
        </div>
      )}

      {tab === "requirements" && (
        <Card className="space-y-4 p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">Job requirements</h2>
            <button className="btn-primary" onClick={saveRequirements} disabled={saving}>{saving ? "Saving…" : "Save requirements"}</button>
          </div>
          <RequirementsEditor requirements={requirements} onChange={setRequirements} />
          <div className="border-t border-slate-100 pt-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Job description</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-600">{job.description || "—"}</p>
          </div>
        </Card>
      )}

      {tab === "settings" && (
        <Card className="space-y-5 p-6">
          <h2 className="font-semibold text-slate-800">Scoring & options</h2>
          <WeightsEditor weights={weights} onChange={setWeights} />
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block text-sm">
              <span className="label">Status</span>
              <select className="input" value={job.status} onChange={(e) => setJob({ ...job, status: e.target.value })}>
                <option value="open">Open</option>
                <option value="draft">Draft</option>
                <option value="closed">Closed</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="label">Experience min</span>
              <input type="number" className="input" value={job.experience_min} onChange={(e) => setJob({ ...job, experience_min: Number(e.target.value) })} />
            </label>
            <label className="block text-sm">
              <span className="label">Experience max</span>
              <input type="number" className="input" value={job.experience_max} onChange={(e) => setJob({ ...job, experience_max: Number(e.target.value) })} />
            </label>
          </div>
          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input type="checkbox" checked={job.blind_screening} onChange={(e) => setJob({ ...job, blind_screening: e.target.checked })} />
            Blind screening
          </label>
          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input type="checkbox" checked={job.feedback_enabled} onChange={(e) => setJob({ ...job, feedback_enabled: e.target.checked })} />
            Show short feedback to candidates
          </label>
          <button className="btn-primary" onClick={saveSettings} disabled={saving}>{saving ? "Saving…" : "Save settings"}</button>
        </Card>
      )}
    </div>
  );
}
