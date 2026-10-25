import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Card, Field, Input, Textarea, useToast } from "../../components/ui";

export default function CandidateProfile() {
  const { push } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", location: "", headline: "", summary: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<any>("/me/profile").then((d) => {
      setProfile(d);
      const p = d.profiles?.[0] || {};
      setForm({
        full_name: p.full_name || d.user.full_name || "",
        email: p.email || d.user.email || "",
        phone: p.phone || "",
        location: p.location || "",
        headline: p.headline || "",
        summary: p.summary || "",
      });
    }).catch((e) => push("error", e.message));
  }, [push]);

  async function save() {
    setBusy(true);
    try {
      await api.patch("/me/profile", form);
      push("success", "Profile saved");
    } catch (e: any) {
      push("error", e.message);
    } finally {
      setBusy(false);
    }
  }

  async function requestDeletion() {
    if (!confirm("Request deletion of your candidate data? Your organization will action this request. This cannot be undone.")) return;
    try {
      await api.post("/me/delete-request", {});
      push("success", "Deletion request submitted");
    } catch (e: any) {
      push("error", e.message);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">My profile</h1>

      <Card className="space-y-4 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name"><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <Field label="Email"><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label="Location"><Input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></Field>
        </div>
        <Field label="Headline"><Input value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} placeholder="e.g. Backend engineer · 6 years" /></Field>
        <Field label="Professional summary"><Textarea rows={4} value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} /></Field>
        <button className="btn-primary" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save profile"}</button>
      </Card>

      <Card className="p-6">
        <h2 className="font-semibold text-slate-800">Privacy & data</h2>
        <p className="mt-2 text-sm text-slate-600">
          You can request deletion of your candidate data at any time. Your organization will review and action the
          request in line with its retention policy.
        </p>
        <button className="btn-danger mt-4" onClick={requestDeletion}>Request data deletion</button>
      </Card>
    </div>
  );
}
