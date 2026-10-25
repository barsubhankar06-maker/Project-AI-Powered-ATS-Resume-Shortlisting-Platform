import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import { Card, Field, Input, Select, Textarea, useToast, Badge } from "../../components/ui";
import { DEFAULT_WEIGHTS, Requirement, RequirementsEditor, WeightsEditor } from "../../components/RequirementsEditor";

export default function JobNew() {
  const navigate = useNavigate();
  const { push } = useToast();
  const [form, setForm] = useState({
    title: "",
    company: "",
    department: "",
    location: "",
    employment_type: "full_time",
    experience_min: 0,
    experience_max: 0,
    description: "",
    responsibilities: "",
    min_qualifications: "",
    preferred_qualifications: "",
    status: "open",
    blind_screening: false,
    feedback_enabled: false,
  });
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS });
  const [analyzing, setAnalyzing] = useState(false);
  const [method, setMethod] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function analyze() {
    if (!form.description.trim()) {
      push("error", "Paste a job description first");
      return;
    }
    setAnalyzing(true);
    try {
      const res = await api.post<any>("/jobs/analyze-jd", { description: form.description, title: form.title });
      setRequirements(res.requirements || []);
      setMethod(res.method);
      const s = res.suggested || {};
      setForm((f) => ({
        ...f,
        experience_min: s.experience_min ?? f.experience_min,
        experience_max: s.experience_max ?? f.experience_max,
      }));
      push("success", `Extracted ${res.requirements.length} requirements — review and edit below.`);
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function save() {
    setError("");
    if (!form.title.trim()) {
      setError("Job title is required");
      return;
    }
    const total = Object.values(weights).reduce((a, b) => a + Number(b || 0), 0);
    if (Math.abs(total - 100) > 0.01) {
      setError("Scoring weights must total 100%");
      return;
    }
    setBusy(true);
    try {
      const job = await api.post<any>("/jobs", { ...form, weights });
      if (requirements.length) {
        await api.post(`/jobs/${job.id}/requirements`, requirements);
      }
      push("success", "Job created");
      navigate(`/app/jobs/${job.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New job</h1>
        <p className="text-sm text-slate-500">Paste a description, extract requirements, then review before saving.</p>
      </div>

      {error && <div role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

      <Card className="space-y-4 p-6">
        <h2 className="font-semibold text-slate-800">Basics</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Job title *"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Company"><Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} /></Field>
          <Field label="Department"><Input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></Field>
          <Field label="Location"><Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></Field>
          <Field label="Employment type">
            <Select value={form.employment_type} onChange={(e) => setForm({ ...form, employment_type: e.target.value })}>
              <option value="full_time">Full time</option>
              <option value="part_time">Part time</option>
              <option value="contract">Contract</option>
              <option value="internship">Internship</option>
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Experience min (yrs)">
              <Input type="number" min={0} value={form.experience_min} onChange={(e) => setForm({ ...form, experience_min: Number(e.target.value) })} />
            </Field>
            <Field label="Experience max (yrs)">
              <Input type="number" min={0} value={form.experience_max} onChange={(e) => setForm({ ...form, experience_max: Number(e.target.value) })} />
            </Field>
          </div>
        </div>
      </Card>

      <Card className="space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">Job description</h2>
          <button className="btn-secondary" onClick={analyze} disabled={analyzing}>
            {analyzing ? "Analyzing…" : "✦ Extract requirements"}
          </button>
        </div>
        <Textarea
          rows={10}
          placeholder="Paste the full job description here, including required skills, responsibilities and qualifications…"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        {method && <Badge tone={method === "ai" ? "brand" : "slate"}>Extracted using: {method}</Badge>}
      </Card>

      <Card className="space-y-4 p-6">
        <h2 className="font-semibold text-slate-800">Requirements</h2>
        <RequirementsEditor requirements={requirements} onChange={setRequirements} />
      </Card>

      <Card className="space-y-4 p-6">
        <h2 className="font-semibold text-slate-800">Scoring weights</h2>
        <WeightsEditor weights={weights} onChange={setWeights} />
      </Card>

      <Card className="space-y-4 p-6">
        <h2 className="font-semibold text-slate-800">Options</h2>
        <label className="flex items-center gap-3 text-sm text-slate-700">
          <input type="checkbox" checked={form.blind_screening} onChange={(e) => setForm({ ...form, blind_screening: e.target.checked })} />
          Blind screening (hide candidate identity in ranking views)
        </label>
        <label className="flex items-center gap-3 text-sm text-slate-700">
          <input type="checkbox" checked={form.feedback_enabled} onChange={(e) => setForm({ ...form, feedback_enabled: e.target.checked })} />
          Allow candidates to see short feedback for this role
        </label>
        <Field label="Status">
          <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option value="open">Open</option>
            <option value="draft">Draft</option>
            <option value="closed">Closed</option>
          </Select>
        </Field>
      </Card>

      <div className="flex justify-end gap-3">
        <button className="btn-secondary" onClick={() => navigate("/app/jobs")}>Cancel</button>
        <button className="btn-primary" onClick={save} disabled={busy}>{busy ? "Saving…" : "Create job"}</button>
      </div>
    </div>
  );
}
