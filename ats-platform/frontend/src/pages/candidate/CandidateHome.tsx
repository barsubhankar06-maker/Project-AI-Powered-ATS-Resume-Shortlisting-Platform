import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";

const STAGE_LABELS: Record<string, string> = {
  applied: "Applied", resume_review: "Resume review", shortlisted: "Shortlisted", interview: "Interview",
  assessment: "Assessment", offer: "Offer", hired: "Hired", rejected: "Rejected",
};

export default function CandidateHome() {
  const { push } = useToast();
  const [apps, setApps] = useState<any[] | null>(null);

  useEffect(() => {
    api.get<any[]>("/me/applications").then(setApps).catch((e) => push("error", e.message));
  }, [push]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My applications</h1>
          <p className="text-sm text-slate-500">Track the status of every role you've applied to.</p>
        </div>
        <Link to="/jobs" className="btn-primary">Browse open roles</Link>
      </div>

      {apps === null ? (
        <div className="space-y-2">{[1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
      ) : apps.length === 0 ? (
        <EmptyState
          title="No applications yet"
          message="Browse open roles and apply with your resume to get started."
          action={<Link to="/jobs" className="btn-primary">Browse jobs</Link>}
        />
      ) : (
        <div className="space-y-3">
          {apps.map((a) => (
            <Card key={a.application_id} className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div>
                <h2 className="font-semibold text-slate-800">{a.job_title}</h2>
                <p className="text-sm text-slate-500">{a.company}</p>
                <p className="mt-1 text-xs text-slate-400">Applied {new Date(a.applied_at).toLocaleDateString()}</p>
                {a.feedback && (
                  <div className="mt-2 rounded-lg bg-brand-50 p-2 text-xs text-brand-800">
                    <strong>Feedback:</strong> {a.feedback}
                  </div>
                )}
              </div>
              <Badge tone={a.stage === "rejected" ? "red" : a.stage === "hired" ? "green" : "brand"}>
                {STAGE_LABELS[a.stage] || a.stage}
              </Badge>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
