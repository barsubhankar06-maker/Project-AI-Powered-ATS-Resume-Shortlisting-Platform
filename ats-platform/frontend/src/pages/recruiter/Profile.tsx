import { useState } from "react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { Badge, Card, Field, Input, useToast } from "../../components/ui";

export default function Profile() {
  const { me } = useAuth();
  const { push } = useToast();
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [busy, setBusy] = useState(false);

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
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Profile</h1>

      <Card className="p-6">
        <h2 className="mb-4 font-semibold text-slate-800">Your account</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between"><dt className="text-slate-500">Name</dt><dd className="font-medium text-slate-800">{me?.user.full_name}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Email</dt><dd className="font-medium text-slate-800">{me?.user.email}</dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Role</dt><dd><Badge tone="brand">{me?.active_role}</Badge></dd></div>
          <div className="flex justify-between"><dt className="text-slate-500">Memberships</dt><dd className="text-slate-700">{me?.memberships.map((m) => `${m.org_name} (${m.role})`).join(", ") || "—"}</dd></div>
        </dl>
      </Card>

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
