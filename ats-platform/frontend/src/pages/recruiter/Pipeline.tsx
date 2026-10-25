import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge, ScoreBadge, Skeleton, useToast } from "../../components/ui";

const STAGES = ["applied", "resume_review", "shortlisted", "interview", "assessment", "offer", "hired", "rejected"];
const STAGE_LABELS: Record<string, string> = {
  applied: "Applied", resume_review: "Resume review", shortlisted: "Shortlisted", interview: "Interview",
  assessment: "Assessment", offer: "Offer", hired: "Hired", rejected: "Rejected",
};

export default function Pipeline() {
  const { jobId = "" } = useParams();
  const { push } = useToast();
  const [data, setData] = useState<any>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setData(await api.get<any>(`/applications/pipeline/${jobId}`));
  }, [jobId]);

  useEffect(() => {
    load().catch((e) => push("error", e.message));
  }, [load, push]);

  async function move(appId: string, stage: string) {
    try {
      await api.post(`/applications/${appId}/stage`, { stage, note: "moved via pipeline" });
      push("success", `Moved to ${STAGE_LABELS[stage]}`);
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  if (!data) return <Skeleton className="h-96 w-full" />;

  return (
    <div className="space-y-6">
      <div>
        <Link to={`/app/jobs/${jobId}`} className="text-sm text-brand-600 hover:underline">← Back to job</Link>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Pipeline · {data.job_title}</h1>
        <p className="text-sm text-slate-500">Drag candidates between stages, or use the buttons. Every change is audited.</p>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => {
          const items = data.columns[stage] || [];
          return (
            <div
              key={stage}
              onDragOver={(e) => {
                e.preventDefault();
                setOverStage(stage);
              }}
              onDragLeave={() => setOverStage(null)}
              onDrop={() => {
                if (dragId) move(dragId, stage);
                setDragId(null);
                setOverStage(null);
              }}
              className={`flex w-64 flex-none flex-col rounded-xl border p-3 transition ${
                overStage === stage ? "border-brand-400 bg-brand-50" : "border-slate-200 bg-slate-50"
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-700">{STAGE_LABELS[stage]}</h2>
                <Badge>{items.length}</Badge>
              </div>
              <div className="flex-1 space-y-2">
                {items.map((c: any) => (
                  <div
                    key={c.application_id}
                    draggable
                    onDragStart={() => setDragId(c.application_id)}
                    onDragEnd={() => setDragId(null)}
                    className="cursor-grab rounded-lg border border-slate-200 bg-white p-3 shadow-sm active:cursor-grabbing"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <Link to={`/app/candidates/${c.candidate_id}`} className="text-sm font-medium text-slate-800 hover:text-brand-600">
                        {c.display_name}
                      </Link>
                      <ScoreBadge score={c.score} />
                    </div>
                    {c.resume_filename && <div className="mt-1 truncate text-xs text-slate-400">{c.resume_filename}</div>}
                    <div className="mt-2 flex gap-1">
                      {STAGES.filter((s) => s !== stage)
                        .slice(0, 2)
                        .map((s) => (
                          <button
                            key={s}
                            onClick={() => move(c.application_id, s)}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200"
                            title={`Move to ${STAGE_LABELS[s]}`}
                          >
                            → {STAGE_LABELS[s].split(" ")[0]}
                          </button>
                        ))}
                    </div>
                  </div>
                ))}
                {items.length === 0 && <p className="text-xs text-slate-400">Drop candidates here</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
