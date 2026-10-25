import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Field, Input, ScoreBadge, Skeleton, Textarea, useToast } from "../../components/ui";

const STAGES = ["applied", "resume_review", "shortlisted", "interview", "assessment", "offer", "hired", "rejected"];
const STAGE_LABELS: Record<string, string> = {
  applied: "Applied", resume_review: "Resume review", shortlisted: "Shortlisted", interview: "Interview",
  assessment: "Assessment", offer: "Offer", hired: "Hired", rejected: "Rejected",
};

export default function CandidateDetail() {
  const { candidateId = "" } = useParams();
  const { push } = useToast();
  const [data, setData] = useState<any>(null);
  const [activeApp, setActiveApp] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [feedback, setFeedback] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [note, setNote] = useState("");
  const [fb, setFb] = useState({ rating: 3, strengths: "", weaknesses: "", notes: "" });
  const [parsed, setParsed] = useState<string>("");

  const load = useCallback(async () => {
    const d = await api.get<any>(`/candidates/${candidateId}`);
    setData(d);
    if (d.applications.length && !activeApp) setActiveApp(d.applications[0].application_id);
  }, [candidateId, activeApp]);

  useEffect(() => {
    load().catch((e) => push("error", e.message));
  }, [load, push]);

  const loadApp = useCallback(async (appId: string) => {
    const [det, n, f, t, p] = await Promise.all([
      api.get<any>(`/applications/${appId}`),
      api.get<any[]>(`/applications/${appId}/notes`),
      api.get<any[]>(`/applications/${appId}/feedback`),
      api.get<any[]>(`/applications/${appId}/timeline`),
      api.get<any>(`/candidates/applications/${appId}/parsed`),
    ]);
    setDetail(det);
    setNotes(n);
    setFeedback(f);
    setTimeline(t);
    setParsed(JSON.stringify(p.parsed || {}, null, 2));
  }, []);

  useEffect(() => {
    if (activeApp) loadApp(activeApp).catch((e) => push("error", e.message));
  }, [activeApp, loadApp, push]);

  async function changeStage(stage: string) {
    if (!activeApp) return;
    try {
      await api.post(`/applications/${activeApp}/stage`, { stage, note: "" });
      push("success", `Moved to ${STAGE_LABELS[stage]}`);
      loadApp(activeApp);
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  async function addNote() {
    if (!note.trim() || !activeApp) return;
    await api.post(`/applications/${activeApp}/notes`, { body: note });
    setNote("");
    loadApp(activeApp);
    push("success", "Note added");
  }

  async function addFeedback() {
    if (!activeApp) return;
    await api.post(`/applications/${activeApp}/feedback`, { ...fb, stage: "interview" });
    setFb({ rating: 3, strengths: "", weaknesses: "", notes: "" });
    loadApp(activeApp);
    push("success", "Feedback recorded");
  }

  async function rerun() {
    if (!activeApp) return;
    try {
      await api.post(`/candidates/applications/${activeApp}/rematch`);
      push("success", "Matching re-run");
      loadApp(activeApp);
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  async function saveParsed() {
    if (!detail?.resume_id) {
      push("error", "No resume to edit");
      return;
    }
    try {
      const obj = JSON.parse(parsed);
      await api.patch(`/resumes/${detail.resume_id}/parsed`, { data: obj });
      push("success", "Parsed data saved and matching re-run");
      loadApp(activeApp!);
    } catch (e: any) {
      push("error", e.message || "Invalid JSON");
    }
  }

  async function downloadResume() {
    if (!detail?.resume_id) return;
    const res = await api.get<{ url: string }>(`/resumes/${detail.resume_id}/download-url`);
    window.open(res.url, "_blank");
  }

  if (!data) return <div className="space-y-4"><Skeleton className="h-10 w-1/3" /><Skeleton className="h-64 w-full" /></div>;

  const cand = data.candidate;
  const match = detail?.latest_match;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/app/candidates" className="text-sm text-brand-600 hover:underline">← Candidates</Link>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{cand.full_name || "Unnamed candidate"}</h1>
        <p className="text-sm text-slate-500">{[cand.email, cand.phone, cand.location].filter(Boolean).join(" · ")}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: applications + profile */}
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Applications</h2>
            {data.applications.length === 0 ? (
              <EmptyState title="No applications" />
            ) : (
              <ul className="space-y-2">
                {data.applications.map((a: any) => (
                  <li key={a.application_id}>
                    <button
                      onClick={() => setActiveApp(a.application_id)}
                      className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                        activeApp === a.application_id ? "border-brand-400 bg-brand-50" : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-800">{a.job_title}</span>
                        <ScoreBadge score={a.match_score} />
                      </div>
                      <span className="text-xs text-slate-500">{STAGE_LABELS[a.stage] || a.stage}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Resumes</h2>
            <ul className="space-y-2 text-sm">
              {data.resumes.map((r: any) => (
                <li key={r.id} className="flex items-center justify-between">
                  <span className="truncate text-slate-700">{r.filename}</span>
                  <Badge tone={r.status === "completed" ? "green" : r.status === "failed" ? "red" : "amber"}>{r.status}</Badge>
                </li>
              ))}
            </ul>
            {detail?.resume_id && (
              <button className="btn-secondary mt-3 w-full" onClick={downloadResume}>Download original</button>
            )}
          </Card>
        </div>

        {/* Right: match detail */}
        <div className="space-y-4 lg:col-span-2">
          {!detail ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <>
              <Card className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-slate-800">Match score</h2>
                    <p className="text-xs text-slate-500">
                      Method: <Badge tone={match?.method === "hybrid" ? "brand" : "slate"}>{match?.method || "n/a"}</Badge>
                      {match?.is_stale && <span className="ml-2 text-amber-600">stale — job or resume changed</span>}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <ScoreBadge score={match?.total_score} />
                    <button className="btn-secondary" onClick={rerun}>Re-run matching</button>
                  </div>
                </div>

                {match?.breakdown?.components && (
                  <div className="mt-4 space-y-2">
                    {Object.entries(match.breakdown.components).map(([k, c]: any) => (
                      <div key={k}>
                        <div className="flex justify-between text-xs text-slate-600">
                          <span className="capitalize">{k.replace("_", " ")} · weight {c.weight}%</span>
                          <span>{c.score?.toFixed(0)}/100</span>
                        </div>
                        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                          <div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.min(100, c.score || 0)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <p className="mt-3 text-xs text-slate-400">
                  Scores are decision support only — not a probability of hiring success, and never an automatic rejection.
                </p>
              </Card>

              {match && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <Card className="p-5">
                    <h3 className="mb-2 text-sm font-semibold text-emerald-700">Matched requirements</h3>
                    {match.matched.length ? (
                      <div className="flex flex-wrap gap-1.5">{match.matched.map((s: string) => <Badge key={s} tone="green">{s}</Badge>)}</div>
                    ) : <p className="text-sm text-slate-400">None</p>}
                    {match.partial?.length > 0 && (
                      <>
                        <h3 className="mb-2 mt-4 text-sm font-semibold text-amber-700">Partial / transferable</h3>
                        <div className="flex flex-wrap gap-1.5">
                          {match.partial.map((p: any, i: number) => <Badge key={i} tone="amber">{p.skill} (via {p.via?.join(", ")})</Badge>)}
                        </div>
                      </>
                    )}
                  </Card>
                  <Card className="p-5">
                    <h3 className="mb-2 text-sm font-semibold text-rose-700">Missing / unverified</h3>
                    {match.missing.length ? (
                      <div className="flex flex-wrap gap-1.5">{match.missing.map((s: string) => <Badge key={s} tone="red">{s}</Badge>)}</div>
                    ) : <p className="text-sm text-slate-400">None</p>}
                    {match.uncertainties?.length > 0 && (
                      <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-slate-500">
                        {match.uncertainties.map((u: string, i: number) => <li key={i}>{u}</li>)}
                      </ul>
                    )}
                  </Card>
                </div>
              )}

              {match?.evidence?.length > 0 && (
                <Card className="p-5">
                  <h3 className="mb-2 text-sm font-semibold text-slate-700">Supporting evidence</h3>
                  <ul className="space-y-2 text-sm text-slate-600">
                    {match.evidence.map((e: any, i: number) => (
                      <li key={i} className="rounded-lg bg-slate-50 p-3">
                        {e.text}
                        <div className="mt-1 flex flex-wrap gap-1">
                          {e.matches?.map((m: string) => <Badge key={m} tone="brand">{m}</Badge>)}
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Stage + timeline */}
              <Card className="p-5">
                <h3 className="mb-3 text-sm font-semibold text-slate-700">Hiring stage</h3>
                <div className="flex flex-wrap gap-2">
                  {STAGES.map((s) => (
                    <button
                      key={s}
                      onClick={() => changeStage(s)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                        detail.stage === s ? "bg-brand-600 text-white" : "border border-slate-300 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {STAGE_LABELS[s]}
                    </button>
                  ))}
                </div>
                {timeline.length > 0 && (
                  <ol className="mt-4 space-y-2 border-l border-slate-200 pl-4 text-sm">
                    {timeline.map((t, i) => (
                      <li key={i} className="relative">
                        <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-brand-500" />
                        <span className="font-medium text-slate-700">{STAGE_LABELS[t.to] || t.to}</span>
                        <span className="ml-2 text-xs text-slate-400">{new Date(t.at).toLocaleString()}</span>
                        {t.note && <div className="text-xs text-slate-500">{t.note}</div>}
                      </li>
                    ))}
                  </ol>
                )}
              </Card>

              {/* Notes & feedback */}
              <div className="grid gap-4 sm:grid-cols-2">
                <Card className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-slate-700">Recruiter notes</h3>
                  <div className="space-y-2">
                    <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a note…" />
                    <button className="btn-secondary w-full" onClick={addNote}>Add note</button>
                  </div>
                  <ul className="mt-3 space-y-2 text-sm">
                    {notes.map((n) => (
                      <li key={n.id} className="rounded-lg bg-slate-50 p-2">
                        <p className="text-slate-700">{n.body}</p>
                        <span className="text-xs text-slate-400">{new Date(n.at).toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card className="p-5">
                  <h3 className="mb-3 text-sm font-semibold text-slate-700">Interview feedback</h3>
                  <div className="space-y-2">
                    <Field label="Rating (0–5)">
                      <Input type="number" min={0} max={5} value={fb.rating} onChange={(e) => setFb({ ...fb, rating: Number(e.target.value) })} />
                    </Field>
                    <Input placeholder="Strengths" value={fb.strengths} onChange={(e) => setFb({ ...fb, strengths: e.target.value })} />
                    <Input placeholder="Weaknesses" value={fb.weaknesses} onChange={(e) => setFb({ ...fb, weaknesses: e.target.value })} />
                    <button className="btn-secondary w-full" onClick={addFeedback}>Record feedback</button>
                  </div>
                  <ul className="mt-3 space-y-2 text-sm">
                    {feedback.map((f) => (
                      <li key={f.id} className="rounded-lg bg-slate-50 p-2">
                        <div className="flex justify-between"><span className="font-medium">Rating {f.rating}/5</span></div>
                        <p className="text-slate-600">{f.strengths} {f.weaknesses}</p>
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>

              {/* Parsed data editor */}
              <Card className="p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-700">Parsed resume data (editable)</h3>
                  <button className="btn-secondary" onClick={saveParsed}>Save & re-match</button>
                </div>
                <Textarea rows={14} className="font-mono text-xs" value={parsed} onChange={(e) => setParsed(e.target.value)} />
                <p className="mt-2 text-xs text-slate-400">
                  Correct any parsing errors here. Unknown fields are marked null rather than assumed absent.
                </p>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
