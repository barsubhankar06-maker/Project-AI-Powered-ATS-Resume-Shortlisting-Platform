import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";

export default function Jobs() {
  const [jobs, setJobs] = useState<any[] | null>(null);
  const [filter, setFilter] = useState("");
  const { push } = useToast();

  async function load() {
    const path = filter ? `/jobs?status=${filter}` : "/jobs";
    setJobs(await api.get<any[]>(path));
  }
  useEffect(() => {
    load().catch((e) => push("error", e.message));
  }, [filter]);

  async function remove(id: string, title: string) {
    if (!confirm(`Delete "${title}"? This also removes its applications and match results. This cannot be undone.`)) return;
    try {
      await api.del(`/jobs/${id}`);
      push("success", "Job deleted");
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500">Create roles, attach requirements and screen candidates.</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="input w-40" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="draft">Draft</option>
            <option value="closed">Closed</option>
          </select>
          <Link to="/app/jobs/new" className="btn-primary">New job</Link>
        </div>
      </div>

      {jobs === null ? (
        <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
      ) : jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          message="Create your first job and paste a description to auto-extract its requirements."
          action={<Link to="/app/jobs/new" className="btn-primary">Create a job</Link>}
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-5 py-3 font-medium">Location</th>
                <th className="px-5 py-3 font-medium">Experience</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((j) => (
                <tr key={j.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <Link to={`/app/jobs/${j.id}`} className="font-medium text-slate-800 hover:text-brand-600">{j.title}</Link>
                    <div className="text-xs text-slate-400">{j.department}</div>
                  </td>
                  <td className="px-5 py-3 text-slate-600">{j.location || "—"}</td>
                  <td className="px-5 py-3 text-slate-600">
                    {j.experience_min || j.experience_max ? `${j.experience_min}–${j.experience_max} yrs` : "—"}
                  </td>
                  <td className="px-5 py-3">
                    <Badge tone={j.status === "open" ? "green" : j.status === "closed" ? "slate" : "amber"}>{j.status}</Badge>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2">
                      <Link to={`/app/jobs/${j.id}`} className="text-brand-600 hover:underline">Open</Link>
                      <button className="text-rose-600 hover:underline" onClick={() => remove(j.id, j.title)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
