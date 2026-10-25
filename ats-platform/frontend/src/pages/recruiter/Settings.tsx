import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Badge, Card, Field, Input, useToast } from "../../components/ui";

export default function Settings() {
  const { me } = useAuth();
  const { push } = useToast();
  const [config, setConfig] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<any>("/public/config").then(setConfig).catch(() => {});
    api.get<any>("/admin/system-health").then(setHealth).catch(() => {});
  }, []);

  async function changePassword() {
    if (pw.new_password.length < 8) {
      push("error", "New password must be at least 8 characters");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/change-password", pw);
      push("success", "Password updated");
      setPw({ current_password: "", new_password: "" });
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Workspace, matching engine and account security.</p>
      </div>

      <Card className="p-6">
        <h2 className="mb-3 font-semibold text-slate-800">Workspace</h2>
        <dl className="grid gap-3 sm:grid-cols-2 text-sm">
          <div><dt className="text-slate-500">Organization</dt><dd className="font-medium text-slate-800">{me?.memberships?.[0]?.org_name || "—"}</dd></div>
          <div><dt className="text-slate-500">Your role</dt><dd className="font-medium text-slate-800 capitalize">{me?.active_role || "—"}</dd></div>
        </dl>
      </Card>

      <Card className="p-6">
        <h2 className="mb-3 font-semibold text-slate-800">Matching engine</h2>
        {config ? (
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-600">AI enrichment</span>
              <Badge tone={config.ai_configured ? "green" : "slate"}>
                {config.ai_configured ? `Configured (${config.ai_model})` : "Not configured — deterministic engine active"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600">OCR for scanned PDFs</span>
              <Badge tone={config.ocr_enabled ? "green" : "slate"}>{config.ocr_enabled ? "Enabled" : "Disabled"}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600">Storage backend</span>
              <Badge tone="blue">{config.storage_backend}</Badge>
            </div>
            <div>
              <span className="text-slate-600">Default scoring weights</span>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(config.scoring_weights).map(([k, v]) => (
                  <Badge key={k} tone="brand">{k.replace("_", " ")}: {v as number}%</Badge>
                ))}
              </div>
            </div>
            <p className="text-xs text-slate-400">
              The deterministic engine always runs. AI enrichment is optional and clearly labelled on each result.
            </p>
          </div>
        ) : <p className="text-sm text-slate-400">Loading…</p>}
      </Card>

      {health && (
        <Card className="p-6">
          <h2 className="mb-3 font-semibold text-slate-800">Processing health</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div><dt className="text-slate-500">Resumes</dt><dd className="text-xl font-bold">{health.resumes_total}</dd></div>
            <div><dt className="text-slate-500">Processing</dt><dd className="text-xl font-bold">{health.resumes_processing}</dd></div>
            <div><dt className="text-slate-500">Failed</dt><dd className="text-xl font-bold text-rose-600">{health.resumes_failed}</dd></div>
            <div><dt className="text-slate-500">Mode</dt><dd className="text-sm font-medium">{health.config.processing_mode}</dd></div>
          </dl>
        </Card>
      )}

      <Card className="p-6">
        <h2 className="mb-3 font-semibold text-slate-800">Change password</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Current password"><Input type="password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field label="New password"><Input type="password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
        </div>
        <button className="btn-primary mt-4" onClick={changePassword} disabled={busy}>{busy ? "Saving…" : "Update password"}</button>
      </Card>
    </div>
  );
}
