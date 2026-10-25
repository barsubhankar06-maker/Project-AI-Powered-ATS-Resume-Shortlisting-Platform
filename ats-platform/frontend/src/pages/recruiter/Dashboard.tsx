import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../../lib/api";
import { Card, EmptyState, ScoreBadge, Skeleton } from "../../components/ui";

const STAGE_LABELS: Record<string, string> = {
  applied: "Applied",
  resume_review: "Resume review",
  shortlisted: "Shortlisted",
  interview: "Interview",
  assessment: "Assessment",
  offer: "Offer",
  hired: "Hired",
  rejected: "Rejected",
};
const COLORS = ["#6366f1", "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#14b8a6", "#22c55e", "#f43f5e"];

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/analytics/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  if (!data)
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)}
        </div>
      </div>
    );

  const cards = [
    ["Active jobs", data.active_jobs, "/app/jobs"],
    ["Total applications", data.total_applications, "/app/candidates"],
    ["Resumes processed", data.resumes_processed, "/app/screening"],
    ["Shortlisted", data.shortlisted, "/app/candidates"],
    ["Awaiting review", data.awaiting_review, "/app/candidates"],
    ["Avg. match score", data.avg_match_score ?? "—", "/app/reports"],
  ];

  const stageData = Object.entries(data.stage_distribution || {}).map(([k, v]) => ({
    stage: STAGE_LABELS[k] || k,
    count: v as number,
  }));
  const pieData = stageData.filter((s) => s.count > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Live figures computed from your organization's records.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map(([label, value, to]) => (
          <Link key={label as string} to={to as string} className="card p-5 transition hover:shadow-md">
            <div className="text-sm text-slate-500">{label as string}</div>
            <div className="mt-2 text-3xl font-bold text-slate-900">{value as any}</div>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Candidates by hiring stage</h2>
          {stageData.every((s) => s.count === 0) ? (
            <EmptyState title="No applications yet" message="Upload resumes against a job to populate the pipeline." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={stageData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="stage" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={60} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Pipeline share</h2>
          {pieData.length === 0 ? (
            <EmptyState title="Nothing to show yet" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} dataKey="count" nameKey="stage" outerRadius={100} label>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">Job-wise statistics</h2>
            <Link to="/app/jobs" className="text-sm text-brand-600 hover:underline">Manage jobs</Link>
          </div>
          {data.job_stats?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-2 font-medium">Job</th>
                    <th className="py-2 font-medium">Applications</th>
                    <th className="py-2 font-medium">Shortlisted</th>
                    <th className="py-2 font-medium">Avg score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.job_stats.map((j: any) => (
                    <tr key={j.job_id}>
                      <td className="py-2">
                        <Link to={`/app/jobs/${j.job_id}`} className="font-medium text-slate-800 hover:text-brand-600">
                          {j.title}
                        </Link>
                      </td>
                      <td className="py-2 text-slate-600">{j.applications}</td>
                      <td className="py-2 text-slate-600">{j.shortlisted}</td>
                      <td className="py-2"><ScoreBadge score={j.avg_score} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No jobs yet" action={<Link to="/app/jobs/new" className="btn-primary">Create a job</Link>} />
          )}
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Recent activity</h2>
          {data.recent_activity?.length ? (
            <ul className="space-y-3">
              {data.recent_activity.map((a: any) => (
                <li key={a.application_id} className="flex items-center justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-700">{a.candidate}</div>
                    <div className="truncate text-xs text-slate-500">{a.job}</div>
                  </div>
                  <span className="whitespace-nowrap text-xs text-slate-500">{STAGE_LABELS[a.stage] || a.stage}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No activity yet" />
          )}
        </Card>
      </div>
    </div>
  );
}
