import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { Card, EmptyState, Skeleton, useToast } from "../../components/ui";

export default function Candidates() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [jobId, setJobId] = useState("");
  const { push } = useToast();

  useEffect(() => {
    api.get<any[]>("/jobs").then(setJobs).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (jobId) params.set("job_id", jobId);
    const t = setTimeout(() => {
      api.get<any[]>(`/candidates?${params.toString()}`).then(setRows).catch((e) => push("error", e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [q, jobId, push]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Candidates</h1>
        <p className="text-sm text-slate-500">Everyone in your organization's talent pool.</p>
      </div>

      <Card className="flex flex-wrap gap-3 p-4">
        <input className="input flex-1" placeholder="Search by name or email…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input w-56" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          <option value="">All jobs</option>
          {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </Card>

      {rows === null ? (
        <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No candidates found" message="Upload resumes against a job to build your talent pool." />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Location</th>
                <th className="px-5 py-3 font-medium">Added</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <Link to={`/app/candidates/${c.id}`} className="font-medium text-slate-800 hover:text-brand-600">
                      {c.full_name || "Unnamed candidate"}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-slate-600">{c.email || "—"}</td>
                  <td className="px-5 py-3 text-slate-600">{c.location || "—"}</td>
                  <td className="px-5 py-3 text-xs text-slate-500">{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
