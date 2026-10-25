import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { Badge } from "../../components/ui";

const features = [
  { title: "Structured resume parsing", body: "PDF & DOCX resumes become clean, editable fields — skills, experience, education, projects — with uncertainty flagged, never guessed." },
  { title: "Explainable match scoring", body: "A transparent 0–100 score broken into required skills, experience, preferred skills, projects and qualifications. Every number is traceable to resume evidence." },
  { title: "Semantic, not keyword-only", body: "Responsibilities and experience are compared semantically, and transferable skills are surfaced instead of silently discarded." },
  { title: "Human-in-the-loop shortlisting", body: "Ranked candidate tables, bulk actions and a visual pipeline. AI is decision support — it never auto-rejects on its own." },
  { title: "Fairness by design", body: "Names, photos, gender, age, ethnicity and other protected attributes are excluded from scoring, with optional blind screening." },
  { title: "Analytics & exports", body: "Pipeline conversion, score distribution, parsing success and frequently missing skills — with CSV export and printable reports." },
];

const steps = [
  { n: "1", t: "Create a job", d: "Paste a job description; the analyzer extracts required skills, responsibilities and qualifications for you to review and edit." },
  { n: "2", t: "Upload resumes", d: "Drag in PDFs or DOCX files in bulk. Each is validated, stored privately and queued for parsing with live status." },
  { n: "3", t: "Review the match", d: "See an explainable score, matched and missing requirements, supporting evidence and parsing uncertainties for every candidate." },
  { n: "4", t: "Shortlist & report", d: "Filter, sort, shortlist and move candidates through the pipeline, then export reports for the hiring team." },
];

export default function Home() {
  const [stats, setStats] = useState<any>(null);
  useEffect(() => {
    api.get("/public/stats").then(setStats).catch(() => {});
  }, []);

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-brand-50 via-white to-white" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <div className="animate-fade-up">
            <Badge tone="brand">Explainable AI screening</Badge>
            <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
              Shortlist the right candidates, and show your work.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600">
              TalentLens parses resumes, matches them against your job requirements, and produces an
              explainable match score you can actually defend — so your hiring team moves faster without
              giving up human judgement.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" className="btn-primary px-6 py-3 text-base">Start free</Link>
              <Link to="/how-it-works" className="btn-secondary px-6 py-3 text-base">See how it works</Link>
            </div>
            {stats && (
              <dl className="mt-10 grid max-w-md grid-cols-3 gap-4">
                {[
                  ["Open roles", stats.jobs],
                  ["Resumes processed", stats.resumes_processed],
                  ["Applications", stats.applications],
                ].map(([label, value]) => (
                  <div key={label as string}>
                    <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
                    <dd className="text-2xl font-bold text-slate-900">{value as number}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>

          {/* Product preview card */}
          <div className="animate-fade-up rounded-2xl border border-slate-200 bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-700">Senior Backend Engineer · ranked candidates</div>
              <Badge tone="blue">Demo data</Badge>
            </div>
            <div className="space-y-3">
              {[
                { name: "Aarav S.", score: 92, missing: 0, tone: "green" },
                { name: "Vikram N.", score: 74, missing: 1, tone: "amber" },
                { name: "Meera I.", score: 58, missing: 3, tone: "amber" },
              ].map((r) => (
                <div key={r.name} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{r.name}</div>
                    <div className="text-xs text-slate-500">Required coverage · {r.missing} missing</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
                      <div className={`h-full rounded-full ${r.score > 80 ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${r.score}%` }} />
                    </div>
                    <span className="w-8 text-right text-sm font-semibold text-slate-700">{r.score}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-slate-400">
              Illustrative screenshot. Scores in your workspace are computed from your own data.
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">Everything a hiring team needs</h2>
          <p className="mt-3 text-slate-600">From raw resume to a defensible shortlist, without black boxes.</p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="card p-6 transition hover:shadow-md">
              <h3 className="text-base font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Steps */}
      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
          <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900">How it works</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-4">
            {steps.map((s) => (
              <div key={s.n} className="relative">
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 font-semibold text-white">{s.n}</div>
                <h3 className="font-semibold text-slate-900">{s.t}</h3>
                <p className="mt-1 text-sm text-slate-600">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="rounded-2xl bg-brand-700 px-8 py-14 text-center shadow-lg">
          <h2 className="text-3xl font-bold text-white">Ready to screen smarter?</h2>
          <p className="mx-auto mt-3 max-w-xl text-brand-100">
            Create an account and try the full workflow with clearly-labelled demo data, or bring your own roles.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link to="/register" className="btn bg-white px-6 py-3 text-base text-brand-700 hover:bg-brand-50">Create free account</Link>
            <Link to="/contact" className="btn border border-brand-300 px-6 py-3 text-base text-white hover:bg-brand-600">Talk to us</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
