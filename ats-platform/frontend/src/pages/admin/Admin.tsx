import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Badge, Card, EmptyState, Skeleton, useToast } from "../../components/ui";

export default function Admin() {
  const { push } = useToast();
  const [tab, setTab] = useState<"users" | "audit" | "health">("users");
  const [users, setUsers] = useState<any[] | null>(null);
  const [logs, setLogs] = useState<any[] | null>(null);
  const [health, setHealth] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      if (tab === "users") setUsers(await api.get<any[]>("/admin/users"));
      if (tab === "audit") setLogs(await api.get<any[]>("/admin/audit-logs?limit=200"));
      if (tab === "health") setHealth(await api.get<any>("/admin/system-health"));
    } catch (e: any) {
      push("error", e.message);
    }
  }, [tab, push]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActive(u: any) {
    try {
      await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
      push("success", `${u.email} ${u.is_active ? "deactivated" : "activated"}`);
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  async function changeRole(u: any, role: string) {
    try {
      await api.patch(`/admin/users/${u.id}`, { role });
      push("success", `${u.email} is now ${role}`);
      load();
    } catch (e: any) {
      push("error", e.message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Platform administration</h1>
        <p className="text-sm text-slate-500">Manage users, review audit logs and monitor processing health.</p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {([["users", "Users"], ["audit", "Audit logs"], ["health", "System health"]] as const).map(([k, l]) => (
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

      {tab === "users" && (
        users === null ? <Skeleton className="h-64 w-full" /> : (
          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Memberships</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-800">{u.full_name}</div>
                      <div className="text-xs text-slate-400">{u.email}</div>
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {u.memberships.map((m: any) => `${m.org_name}: ${m.role}`).join(", ") || "—"}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? "active" : "inactive"}</Badge>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <button className="text-brand-600 hover:underline" onClick={() => toggleActive(u)}>
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                        {u.memberships[0] && (
                          <select
                            className="input w-32 py-1"
                            value={u.memberships[0].role}
                            onChange={(e) => changeRole(u, e.target.value)}
                          >
                            <option value="recruiter">recruiter</option>
                            <option value="admin">admin</option>
                          </select>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {tab === "audit" && (
        logs === null ? <Skeleton className="h-64 w-full" /> : logs.length === 0 ? (
          <EmptyState title="No audit entries" />
        ) : (
          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">When</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                  <th className="px-5 py-3 font-medium">Entity</th>
                  <th className="px-5 py-3 font-medium">Actor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td className="px-5 py-3 text-xs text-slate-500">{new Date(l.at).toLocaleString()}</td>
                    <td className="px-5 py-3"><Badge tone="slate">{l.action}</Badge></td>
                    <td className="px-5 py-3 text-slate-600">{l.entity_type} {l.entity_id ? `· ${l.entity_id.slice(0, 8)}` : ""}</td>
                    <td className="px-5 py-3 text-xs text-slate-500">{l.actor_id ? l.actor_id.slice(0, 8) : "system"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {tab === "health" && (
        health === null ? <Skeleton className="h-64 w-full" /> : (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <h2 className="mb-4 font-semibold text-slate-800">Counts</h2>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                {Object.entries(health.counts).map(([k, v]) => (
                  <div key={k}><dt className="capitalize text-slate-500">{k}</dt><dd className="text-xl font-bold">{v as number}</dd></div>
                ))}
              </dl>
              <h2 className="mb-2 mt-6 font-semibold text-slate-800">Configuration</h2>
              <ul className="space-y-1 text-sm text-slate-600">
                {Object.entries(health.config).map(([k, v]) => (
                  <li key={k} className="flex justify-between"><span className="capitalize">{k.replace(/_/g, " ")}</span><span className="font-medium">{String(v)}</span></li>
                ))}
              </ul>
            </Card>
            <Card className="p-6">
              <h2 className="mb-4 font-semibold text-slate-800">Recent processing failures</h2>
              {health.recent_failures.length === 0 ? (
                <p className="text-sm text-emerald-600">No failures 🎉</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {health.recent_failures.map((f: any) => (
                    <li key={f.id} className="rounded-lg bg-rose-50 p-3">
                      <div className="font-medium text-rose-800">{f.filename}</div>
                      <div className="text-xs text-rose-600">{f.error}</div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        )
      )}
    </div>
  );
}
