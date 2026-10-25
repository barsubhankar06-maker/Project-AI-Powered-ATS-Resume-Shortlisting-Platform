import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";

export default function Reports() {
  const { push } = useToast();
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobId, setJobId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get<any[]>("/jobs").then(setJobs).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (jobId) params.set("job_id", jobId);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    setData(null);
    api.get<any>(`/analytics/reports?${params.toString()}`).then(setData).catch((e) => push("error", e.message));
  }, [jobId, dateFrom, dateTo, push]);

  function exportCsv() {
    window.open(`/api/analytics/export.csv${jobId ? `?job_id=${jobId}` : ""}`, "_blank");
  }

  const jobsData = data ? Object.entries(data.applications_by_job).map(([name, count]) => ({ name, count })) : [];
  const scoreData = data ? Object.entries(data.score_distribution).map(([range, count]) => ({ range, count })) : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-sm text-slate-500">Descriptive analytics for your pipeline. Not predictive estimates.</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => window.print()}>Print</button>
          <button className="btn-primary" onClick={exportCsv}>Export CSV</button>
        </div>
      </div>

      <Card className="flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          <span className="label">Job</span>
          <select className="input w-56" value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">All jobs</option>
            {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
          </select>
        </label>
        <label className="text-sm">
          <span className="label">From</span>
          <input type="date" className="input" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="label">To</span>
          <input type="date" className="input" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
      </Card>

      {!data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full" />)}</div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Applications", data.totals.applications],
              ["Scored", data.totals.scored],
              ["Average score", data.totals.avg_score ?? "—"],
              ["Shortlist rate", `${data.totals.shortlist_rate}%`],
            ].map(([l, v]) => (
              <Card key={l as string} className="p-5">
                <div className="text-sm text-slate-500">{l as string}</div>
                <div className="mt-1 text-3xl font-bold text-slate-900">{v as any}</div>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-5">
              <h2 className="mb-4 font-semibold text-slate-800">Applications by job</h2>
              {jobsData.length ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={jobsData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <EmptyState title="No applications in range" />}
            </Card>

            <Card className="p-5">
              <h2 className="mb-4 font-semibold text-slate-800">Candidate distribution by score range</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={scoreData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {scoreData.map((_, i) => <Cell key={i} fill={["#f43f5e", "#f59e0b", "#f59e0b", "#10b981", "#059669"][i]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="p-5">
              <h2 className="mb-3 font-semibold text-slate-800">Pipeline conversion</h2>
              <ul className="space-y-2 text-sm">
                {Object.entries(data.conversion_rates).map(([k, v]) => (
                  <li key={k} className="flex justify-between">
                    <span className="capitalize text-slate-600">{k.replace(/_/g, " → ")}</span>
                    <span className="font-medium text-slate-800">{v as number}%</span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-5">
              <h2 className="mb-3 font-semibold text-slate-800">Resume parsing</h2>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="flex justify-between"><span>Total</span><span className="font-medium">{data.parsing.total}</span></li>
                <li className="flex justify-between"><span>Completed</span><span className="font-medium text-emerald-600">{data.parsing.completed}</span></li>
                <li className="flex justify-between"><span>Failed</span><span className="font-medium text-rose-600">{data.parsing.failed}</span></li>
                <li className="flex justify-between"><span>Success rate</span><span className="font-medium">{data.parsing.success_rate}%</span></li>
              </ul>
              {data.stage_durations_days && Object.keys(data.stage_durations_days).length > 0 && (
                <>
                  <h3 className="mb-2 mt-4 text-sm font-semibold text-slate-700">Avg. days per stage</h3>
                  <ul className="space-y-1 text-sm text-slate-600">
                    {Object.entries(data.stage_durations_days).map(([s, d]) => (
                      <li key={s} className="flex justify-between"><span className="capitalize">{s.replace("_", " ")}</span><span>{d as number}d</span></li>
                    ))}
                  </ul>
                </>
              )}
            </Card>

            <Card className="p-5">
              <h2 className="mb-3 font-semibold text-slate-800">Skills signal</h2>
              <h3 className="mb-1 text-xs font-medium uppercase text-slate-500">Frequently found</h3>
              <div className="mb-3 flex flex-wrap gap-1.5">
                {data.skills_found.length ? data.skills_found.map((s: any) => <Badge key={s.skill} tone="green">{s.skill} · {s.count}</Badge>) : <span className="text-xs text-slate-400">No data</span>}
              </div>
              <h3 className="mb-1 text-xs font-medium uppercase text-slate-500">Frequently missing</h3>
              <div className="flex flex-wrap gap-1.5">
                {data.skills_missing.length ? data.skills_missing.map((s: any) => <Badge key={s.skill} tone="red">{s.skill} · {s.count}</Badge>) : <span className="text-xs text-slate-400">No data</span>}
              </div>
            </Card>
          </div>

          <p className="text-xs text-slate-400">{data.note}</p>
        </>
      )}
    </div>
  );
}
