import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { Logo } from "../../components/MarketingLayout";
import { Field, Input, useToast } from "../../components/ui";

export default function Login() {
  const { login } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const me = await login(email, password);
      push("success", "Welcome back!");
      if (me.memberships.length > 0) navigate("/app/dashboard");
      else navigate("/candidate");
    } catch (err: any) {
      setError(err.message || "Could not sign in");
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
            <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
            <p className="mt-1 text-sm text-slate-500">Sign in to your workspace.</p>
          </div>
          {error && (
            <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          )}
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
          </Field>
          <Field label="Password">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </Field>
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <p className="text-center text-sm text-slate-500">
            New here? <Link to="/register" className="font-medium text-brand-600 hover:underline">Create an account</Link>
          </p>
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
            <p className="font-medium text-slate-600">Demo accounts (seeded on first run)</p>
            <p className="mt-1">Recruiter · recruiter@demo.com / demo12345</p>
            <p>Admin · admin@demo.com / admin12345</p>
            <p>Superadmin · superadmin@platform.local / superadmin12345</p>
          </div>
        </form>
      </div>
    </div>
  );
}
