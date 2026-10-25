import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, Card, EmptyState, ScoreBadge, Skeleton, TableSkeleton, useToast } from "./ui";

interface Row {
  application_id: string;
  candidate_id: string;
  display_name: string;
  email: string;
  resume_filename: string | null;
  match_score: number | null;
  required_coverage: number | null;
  experience_summary: string;
  missing: string[];
  applied_at: string;
  stage: string;
  status: string;
  parsing_status: string;
  method: string | null;
  is_stale: boolean;
}

const STAGES = ["applied", "resume_review", "shortlisted", "interview", "assessment", "offer", "hired", "rejected"];
const STAGE_LABELS: Record<string, string> = {
  applied: "Applied", resume_review: "Resume review", shortlisted: "Shortlisted", interview: "Interview",
  assessment: "Assessment", offer: "Offer", hired: "Hired", rejected: "Rejected",
};

export default function CandidateTable({ jobId }: { jobId: string }) {
  const { push } = useToast();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmAction, setConfirmAction] = useState<{ action: string; label: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [filters, setFilters] = useState({
    score_min: "", score_max: "", coverage_min: "", exp_min: "", exp_max: "",
    skill: "", stage: "", parsing_status: "", sort: "score", order: "desc",
  });

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== "") params.set(k, String(v));
    });
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    try {
      const res = await api.get<{ total: number; items: Row[] }>(`/jobs/${jobId}/candidates?${params.toString()}`);
      setRows(res.items);
      setTotal(res.total);
    } catch (e: any) {
      push("error", e.message);
      setRows([]);
    }
  }, [filters, page, jobId, pageSize, push]);

  useEffect(() => {
    setRows(null);
    load();
  }, [load]);

  function toggle(id: string) {
    setSelected((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }
  function toggleAll() {
    if (!rows) return;
    setSelected((s) => (s.size === rows.length ? new Set() : new Set(rows.map((r) => r.application_id))));
  }

  async function runBulk() {
    if (!confirmAction) return;
    setBusy(true);
    try {
      if (confirmAction.action === "export") {
        window.open(`/api/analytics/export.csv?job_id=${jobId}`, "_blank");
      } else {
        const res = await api.post<{ updated: number }>(`/jobs/${jobId}/bulk`, {
          application_ids: Array.from(selected),
          action: confirmAction.action,
        });
        push("success", `${res.updated} candidate(s) updated`);
      }
      setSelected(new Set());
      load();
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setBusy(false);
      setConfirmAction(null);
    }
  }

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <input className="input" placeholder="Min score" type="number" value={filters.score_min} onChange={(e) => setFilters({ ...filters, score_min: e.target.value })} />
          <input className="input" placeholder="Max score" type="number" value={filters.score_max} onChange={(e) => setFilters({ ...filters, score_max: e.target.value })} />
          <input className="input" placeholder="Min required coverage" type="number" value={filters.coverage_min} onChange={(e) => setFilters({ ...filters, coverage_min: e.target.value })} />
          <input className="input" placeholder="Skill contains" value={filters.skill} onChange={(e) => setFilters({ ...filters, skill: e.target.value })} />
          <input className="input" placeholder="Min experience (yrs)" type="number" value={filters.exp_min} onChange={(e) => setFilters({ ...filters, exp_min: e.target.value })} />
          <input className="input" placeholder="Max experience (yrs)" type="number" value={filters.exp_max} onChange={(e) => setFilters({ ...filters, exp_max: e.target.value })} />
          <select className="input" value={filters.stage} onChange={(e) => setFilters({ ...filters, stage: e.target.value })}>
            <option value="">All stages</option>
            {STAGES.map((s) => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
          </select>
          <select className="input" value={filters.parsing_status} onChange={(e) => setFilters({ ...filters, parsing_status: e.target.value })}>
            <option value="">Any parsing status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <select className="input" value={`${filters.sort}:${filters.order}`} onChange={(e) => {
            const [sort, order] = e.target.value.split(":");
            setFilters({ ...filters, sort, order });
          }}>
            <option value="score:desc">Score (high → low)</option>
            <option value="score:asc">Score (low → high)</option>
            <option value="applied_at:desc">Newest first</option>
            <option value="applied_at:asc">Oldest first</option>
            <option value="name:asc">Name (A → Z)</option>
          </select>
          <button className="btn-secondary" onClick={() => setFilters({ score_min: "", score_max: "", coverage_min: "", exp_min: "", exp_max: "", skill: "", stage: "", parsing_status: "", sort: "score", order: "desc" })}>
            Reset filters
          </button>
        </div>
      </Card>

      {/* Bulk bar */}
      {selected.size > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
          <span className="text-sm font-medium text-brand-800">{selected.size} selected</span>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => setConfirmAction({ action: "shortlist", label: "shortlist" })}>Shortlist</button>
            <button className="btn-secondary" onClick={() => setConfirmAction({ action: "review", label: "move to review" })}>Move to review</button>
            <button className="btn-danger" onClick={() => setConfirmAction({ action: "reject", label: "reject" })}>Reject</button>
            <button className="btn-secondary" onClick={() => setConfirmAction({ action: "export", label: "export" })}>Export CSV</button>
          </div>
        </div>
      )}

      {/* Table */}
      {rows === null ? (
        <TableSkeleton rows={6} />
      ) : rows.length === 0 ? (
        <EmptyState title="No candidates match" message="Adjust filters, or upload resumes for this job." />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-3">
                  <input type="checkbox" aria-label="Select all" checked={selected.size === rows.length && rows.length > 0} onChange={toggleAll} />
                </th>
                <th className="px-3 py-3 font-medium">Candidate</th>
                <th className="px-3 py-3 font-medium">Score</th>
                <th className="px-3 py-3 font-medium">Req. coverage</th>
                <th className="px-3 py-3 font-medium">Experience</th>
                <th className="px-3 py-3 font-medium">Missing / unverified</th>
                <th className="px-3 py-3 font-medium">Stage</th>
                <th className="px-3 py-3 font-medium">Parsing</th>
                <th className="px-3 py-3 font-medium">Applied</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.application_id} className="hover:bg-slate-50">
                  <td className="px-3 py-3">
                    <input type="checkbox" aria-label={`Select ${r.display_name}`} checked={selected.has(r.application_id)} onChange={() => toggle(r.application_id)} />
                  </td>
                  <td className="px-3 py-3">
                    <Link to={`/app/candidates/${r.candidate_id}`} className="font-medium text-slate-800 hover:text-brand-600">{r.display_name}</Link>
                    <div className="text-xs text-slate-400">{r.resume_filename || "no resume"}</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      <ScoreBadge score={r.match_score} />
                      {r.is_stale && <Badge tone="amber">stale</Badge>}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-slate-600">{r.required_coverage != null ? `${r.required_coverage.toFixed(0)}%` : "—"}</td>
                  <td className="px-3 py-3 text-slate-600">{r.experience_summary}</td>
                  <td className="px-3 py-3">
                    {r.missing.length ? (
                      <span className="text-xs text-slate-600">{r.missing.slice(0, 3).join(", ")}{r.missing.length > 3 ? ` +${r.missing.length - 3}` : ""}</span>
                    ) : (
                      <span className="text-xs text-emerald-600">none</span>
                    )}
                  </td>
                  <td className="px-3 py-3"><Badge tone={r.stage === "rejected" ? "red" : r.stage === "hired" ? "green" : "slate"}>{STAGE_LABELS[r.stage] || r.stage}</Badge></td>
                  <td className="px-3 py-3"><Badge tone={r.parsing_status === "completed" ? "green" : r.parsing_status === "failed" ? "red" : "amber"}>{r.parsing_status}</Badge></td>
                  <td className="px-3 py-3 text-xs text-slate-500">{new Date(r.applied_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Pagination */}
      {rows && rows.length > 0 && (
        <div className="flex items-center justify-between text-sm text-slate-600">
          <span>{total} candidate(s)</span>
          <div className="flex items-center gap-2">
            <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
            <span>Page {page} of {pages}</span>
            <button className="btn-secondary" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}

      {/* Confirm dialog */}
      {confirmAction && (
        <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setConfirmAction(null)} />
          <div role="dialog" aria-modal="true" className="relative z-50 w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Confirm {confirmAction.label}</h3>
            <p className="mt-2 text-sm text-slate-600">
              {confirmAction.action === "reject"
                ? `You are about to reject ${selected.size} candidate(s). This is recorded in the audit log and can be reversed by moving them back to another stage.`
                : `Apply "${confirmAction.label}" to ${selected.size} selected candidate(s)?`}
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setConfirmAction(null)}>Cancel</button>
              <button className={confirmAction.action === "reject" ? "btn-danger" : "btn-primary"} onClick={runBulk} disabled={busy}>
                {busy ? "Working…" : `Yes, ${confirmAction.label}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
