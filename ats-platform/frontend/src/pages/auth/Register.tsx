import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { Logo } from "../../components/MarketingLayout";
import { Field, Input, useToast } from "../../components/ui";

export default function Register() {
  const { register } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const [role, setRole] = useState<"recruiter" | "candidate">("recruiter");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", organization_name: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!form.full_name.trim()) errs.full_name = "Please enter your name";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) errs.email = "Enter a valid email";
    if (form.password.length < 8) errs.password = "Use at least 8 characters";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      await register({ ...form, role });
      push("success", "Account created!");
      navigate(role === "recruiter" ? "/app/dashboard" : "/candidate");
    } catch (err: any) {
      setErrors({ form: err.message || "Could not create account" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center"><Logo /></div>
        <form onSubmit={submit} className="card space-y-4 p-8" noValidate>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
            <p className="mt-1 text-sm text-slate-500">Choose how you'll use TalentLens.</p>
          </div>

          <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1" role="tablist">
            {(["recruiter", "candidate"] as const).map((r) => (
              <button
                key={r}
                type="button"
                role="tab"
                aria-selected={role === r}
                onClick={() => setRole(r)}
                className={`rounded-md px-3 py-2 text-sm font-medium capitalize transition ${
                  role === r ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
                }`}
              >
                {r === "recruiter" ? "Recruiter / Employer" : "Candidate"}
              </button>
            ))}
          </div>

          {errors.form && (
            <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {errors.form}
            </div>
          )}

          <Field label="Full name" error={errors.full_name}>
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoComplete="name" />
          </Field>
          {role === "recruiter" && (
            <Field label="Company / organization" hint="The workspace name your team will see.">
              <Input value={form.organization_name} onChange={(e) => setForm({ ...form, organization_name: e.target.value })} autoComplete="organization" />
            </Field>
          )}
          <Field label="Work email" error={errors.email}>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
          </Field>
          <Field label="Password" error={errors.password} hint="At least 8 characters.">
            <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" />
          </Field>

          <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
          <p className="text-center text-xs text-slate-400">
            By continuing you agree to our <Link to="/terms" className="underline">Terms</Link> and{" "}
            <Link to="/privacy" className="underline">Privacy Policy</Link>.
          </p>
          <p className="text-center text-sm text-slate-500">
            Already have an account? <Link to="/login" className="font-medium text-brand-600 hover:underline">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
