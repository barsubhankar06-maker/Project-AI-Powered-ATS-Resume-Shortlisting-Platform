import { Link } from "react-router-dom";
import { Badge } from "../../components/ui";

const plans = [
  {
    name: "Starter",
    price: "₹0",
    cadence: "/month",
    tagline: "For trying the workflow end to end.",
    features: ["1 active job", "50 resumes / month", "Deterministic matching engine", "CSV export", "Community support"],
    cta: "Start free",
    highlight: false,
  },
  {
    name: "Growth",
    price: "₹4,999",
    cadence: "/month",
    tagline: "For growing hiring teams.",
    features: ["10 active jobs", "1,000 resumes / month", "AI enrichment & semantic matching", "Pipeline & analytics", "Blind screening & audit logs", "Priority email support"],
    cta: "Start free trial",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "",
    tagline: "For organizations with compliance needs.",
    features: ["Unlimited jobs & resumes", "SSO & custom roles", "Bring-your-own AI provider", "Custom retention & data residency", "Dedicated support & SLAs"],
    cta: "Contact sales",
    highlight: false,
  },
];

export default function Pricing() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <Badge tone="amber">Sample plans — billing not implemented</Badge>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Simple, sample pricing</h1>
        <p className="mt-4 text-slate-600">
          These plans are illustrative placeholders. No payment processing is wired up in this build — create an account
          and every feature is available for evaluation with clearly-labelled demo data.
        </p>
      </div>

      <div className="mt-12 grid gap-6 lg:grid-cols-3">
        {plans.map((p) => (
          <div
            key={p.name}
            className={`card flex flex-col p-8 ${p.highlight ? "ring-2 ring-brand-500" : ""}`}
          >
            {p.highlight && <Badge tone="brand">Most popular</Badge>}
            <h2 className="mt-3 text-xl font-bold text-slate-900">{p.name}</h2>
            <p className="text-sm text-slate-500">{p.tagline}</p>
            <div className="mt-5 flex items-baseline gap-1">
              <span className="text-4xl font-extrabold text-slate-900">{p.price}</span>
              <span className="text-slate-500">{p.cadence}</span>
            </div>
            <ul className="mt-6 flex-1 space-y-3 text-sm text-slate-600">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <span className="mt-0.5 text-brand-600">✓</span>
                  {f}
                </li>
              ))}
            </ul>
            <Link to={p.name === "Enterprise" ? "/contact" : "/register"} className={`mt-8 ${p.highlight ? "btn-primary" : "btn-secondary"}`}>
              {p.cta}
            </Link>
          </div>
        ))}
      </div>

      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {[
          ["No black-box rejections", "Scores are decision support. Candidates are never automatically rejected by the system alone."],
          ["Your data, your region", "Run on PostgreSQL or Supabase, with private object storage and configurable retention windows."],
          ["Bring your own AI", "Use the deterministic engine, or plug in an OpenAI-compatible provider — keys stay on your server."],
        ].map(([t, d]) => (
          <div key={t} className="card p-6">
            <h3 className="font-semibold text-slate-900">{t}</h3>
            <p className="mt-2 text-sm text-slate-600">{d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
